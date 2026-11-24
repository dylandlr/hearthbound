#!/usr/bin/env python3
"""Meaningful failure/provenance checks without fabricating Minecraft trials."""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from run_colony_reliability_trial import NbtReader, declare, run, world_evidence
from summarize_colony_reliability import (
    PLAN, PLAN_SCHEMA, PROTOCOL_FILES, TRIAL_SCHEMA, accounting_three_of_four, classified_status,
    counters, diagnostic_flags, physical_delivery_accounting, plan_hash, protocol_hash,
    summarize, wilson,
)

COMMIT = "a" * 40
HASH = "b" * 64


def snapshot(done=4, assigned=0):
    return {
        "audit_before": {"done": done, "assigned": assigned, "held": 0, "queued": 0},
        "audit_after": {"done": done, "assigned": assigned, "held": 0, "queued": 0},
        "destination_has_exact_four_wheat": True,
        "source_wheat_absent": [True] * 4,
        "outstanding_claims": 0,
        "history": {"records": 4, "physically_completed": done, "capacity_denials": 0},
    }


def record(item, done=4, assigned=0):
    passed = done == 4 and assigned == 0
    snap = snapshot(done, assigned)
    return {
        "schema": TRIAL_SCHEMA, **item,
        "source_commit": COMMIT, "protocol_sha256": HASH,
        "rcon_log_sha256": HASH, "server_log_sha256": HASH,
        "fixture_passed": passed, "observation_window_completed": True,
        "fresh_world_directory": True,
        "status": classified_status(passed, True, "AssertionError", snap),
        "error_type": None if passed else "AssertionError",
        "terminal_snapshot": snap,
        "world": {
            "level_name": "colony-reliability-" + item["trial_id"],
            "configured_seed": str(item["seed"]), "generated_seed": item["seed"],
            "world_uuid": "00000000-0000-0000-0000-" + str(item["seed"]).zfill(12),
            "level_dat_sha256": HASH, "world_identity_sha256": HASH,
        },
    }


def prospective_plan(item):
    return {
        "schema": PLAN_SCHEMA, **item, "source_commit": COMMIT, "protocol_sha256": HASH,
        "github_run_id": "12345", "github_run_attempt": "1",
        "level_name": "colony-reliability-" + item["trial_id"],
        "declaration_phase": "BEFORE_BUILD_PREFLIGHT",
        "execution_policy": "ONE_ATTEMPT_PER_PLANNED_WORLD",
        "fresh_world_required": True, "motor_diagnostics_required": True,
    }


class CohortTests(unittest.TestCase):
    def setUp(self):
        self.records = [record(item) for item in PLAN]

    def test_all_passed_does_not_resolve_defect(self):
        result = summarize(self.records, expected_commit=COMMIT)
        self.assertTrue(result["all_trials_passed"])
        event = result["three_of_four_accounting_event"]
        self.assertEqual((event["observed"], event["assessable_trials"], event["unknown_trials"]), (0, 5, 0))
        self.assertAlmostEqual(event["wilson_95_interval_among_assessable"][1], 0.43448246, places=6)
        self.assertFalse(result["limits"]["original_reliability_issue_resolved"])

    def test_terminal_diagnostic_patterns_are_disjoint(self):
        distinct = snapshot(done=4, assigned=0)
        distinct["audit_before"]["distinct_completed_citizens"] = 3
        distinct["audit_after"]["distinct_completed_citizens"] = 3
        self.assertEqual(diagnostic_flags(distinct),
                         ["FOUR_DELIVERIES_FEWER_THAN_FOUR_CITIZENS"])
        missing = snapshot(done=3, assigned=0)
        missing["destination_has_exact_four_wheat"] = False
        missing["source_wheat_absent"][0] = False
        self.assertEqual(diagnostic_flags(missing),
                         ["SOURCE_REMAINS_NO_ASSIGNED_TASK"])
        stuck = snapshot(done=3, assigned=1)
        self.assertEqual(diagnostic_flags(stuck),
                         ["PHYSICAL_FOUR_TASK_THREE_ASSIGNED_ONE"])
        self.assertEqual(diagnostic_flags(None), [])
        self.assertEqual(diagnostic_flags(snapshot()), [])

    def test_patterns_do_not_promote_or_exclude_failed_worlds(self):
        records = copy.deepcopy(self.records)
        records[0]["fixture_passed"] = False
        records[0]["status"] = "FIXTURE_ASSERTION_FAILURE"
        records[0]["error_type"] = "AssertionError"
        records[0]["terminal_snapshot"]["audit_before"]["distinct_completed_citizens"] = 3
        records[0]["terminal_snapshot"]["audit_after"]["distinct_completed_citizens"] = 3
        records[1]["fixture_passed"] = False
        records[1]["status"] = "FIXTURE_ASSERTION_FAILURE"
        records[1]["error_type"] = "AssertionError"
        records[1]["terminal_snapshot"]["destination_has_exact_four_wheat"] = False
        records[1]["terminal_snapshot"]["source_wheat_absent"][0] = False
        records[1]["terminal_snapshot"]["audit_before"]["done"] = 3
        records[1]["terminal_snapshot"]["audit_after"]["done"] = 3
        result = summarize(records)
        self.assertFalse(result["all_trials_passed"])
        self.assertEqual(result["statuses"]["FIXTURE_ASSERTION_FAILURE"], 2)
        self.assertEqual(result["terminal_diagnostic_patterns"], {
            "FOUR_DELIVERIES_FEWER_THAN_FOUR_CITIZENS": 1,
            "SOURCE_REMAINS_NO_ASSIGNED_TASK": 1,
        })

    def test_real_signature_is_failure_not_delivery_success(self):
        self.records[2] = record(PLAN[2], done=3, assigned=1)
        result = summarize(self.records)
        self.assertFalse(result["all_trials_passed"])
        event = result["three_of_four_accounting_event"]
        self.assertEqual((event["observed"], event["assessable_trials"]), (1, 5))
        self.assertEqual(event["frequency_among_assessable"], 0.2)
        self.assertEqual(result["statuses"]["ACCOUNTING_THREE_OF_FOUR"], 1)

    def test_additional_accounting_event_includes_two_pending_jobs(self):
        self.records[0] = record(PLAN[0], done=2, assigned=2)
        self.records[1] = record(PLAN[1], done=3, assigned=1)
        result = summarize(self.records)
        event = result["physical_delivery_accounting_event"]
        self.assertEqual((event["observed"], event["assessable_trials"],
                          event["unknown_trials"]), (2, 5, 0))
        self.assertEqual(event["frequency_among_assessable"], 0.4)
        self.assertEqual(event["wilson_95_interval_among_assessable"], wilson(2, 5))
        self.assertEqual(event["planned_cohort_missingness_bounds"], [0.4, 0.4])
        # Both original classifications and the narrow estimator stay intact.
        self.assertEqual(result["statuses"], {
            "ACCOUNTING_THREE_OF_FOUR": 1, "PASS": 3, "TASK_ACCOUNTING_MISMATCH": 1,
        })
        original = result["three_of_four_accounting_event"]
        self.assertEqual((original["observed"], original["assessable_trials"]), (1, 5))
        self.assertEqual(original["frequency_among_assessable"], 0.2)
        self.assertEqual([t["physical_delivery_accounting_event_observed"]
                          for t in result["trials"]], [True, True, False, False, False])

    def test_accounted_and_incomplete_physical_work_are_not_pending_delivery_event(self):
        missing = record(PLAN[0], done=3, assigned=0)
        missing["terminal_snapshot"]["destination_has_exact_four_wheat"] = False
        missing["terminal_snapshot"]["source_wheat_absent"][0] = False
        missing["status"] = "FIXTURE_ASSERTION_FAILURE"
        distinct = record(PLAN[1])
        distinct.update(fixture_passed=False, status="FIXTURE_ASSERTION_FAILURE",
                        error_type="AssertionError")
        for key in ("audit_before", "audit_after"):
            distinct["terminal_snapshot"][key]["distinct_completed_citizens"] = 3
        self.records[:2] = [missing, distinct]
        result = summarize(self.records)
        event = result["physical_delivery_accounting_event"]
        self.assertEqual((event["observed"], event["assessable_trials"]), (0, 5))
        self.assertFalse(result["all_trials_passed"])
        # An early participation assertion is still unknown under the existing
        # full-window rule, even though the physical/accounting probes succeeded.
        self.records[1]["observation_window_completed"] = False
        result = summarize(self.records)
        self.assertEqual(result["physical_delivery_accounting_event"]["unknown_trials"], 1)
        self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 1)

    def test_additional_event_requires_stable_terminal_task_counters(self):
        for change in ({"done": 3, "assigned": 1}, {"held": 1}, {"queued": 1}):
            with self.subTest(change=change):
                item = record(PLAN[0], done=2, assigned=2)
                item["terminal_snapshot"]["audit_after"].update(change)
                result = summarize([item], plan=PLAN[:1])
                self.assertEqual(result["statuses"], {"TASK_ACCOUNTING_MISMATCH": 1})
                self.assertEqual(result["physical_delivery_accounting_event"]["unknown_trials"], 1)
                self.assertIsNone(result["physical_delivery_accounting_event"]["frequency_among_assessable"])
                # This additional conservative denominator does not rewrite the
                # original estimator's eligibility for the same complete trial.
                self.assertEqual(result["three_of_four_accounting_event"]["assessable_trials"], 1)

    def test_impossible_fixture_counts_are_unknown_only_in_additional_estimator(self):
        for change in ({"done": 5, "assigned": 0}, {"assigned": 3}, {"held": 1}):
            with self.subTest(change=change):
                item = record(PLAN[0], done=2, assigned=2)
                for key in ("audit_before", "audit_after"):
                    item["terminal_snapshot"][key].update(change)
                result = summarize([item], plan=PLAN[:1])
                self.assertEqual(result["physical_delivery_accounting_event"]["unknown_trials"], 1)
                self.assertEqual(result["three_of_four_accounting_event"]["assessable_trials"], 1)

    def test_malformed_task_counters_cannot_be_counted_as_negative_events(self):
        for value in (None, "2", True, -1):
            with self.subTest(value=value):
                item = record(PLAN[0], done=2, assigned=2)
                item["terminal_snapshot"]["audit_after"]["done"] = value
                result = summarize([item], plan=PLAN[:1])
                self.assertEqual(result["statuses"], {"INVALID_EVIDENCE": 1})
                self.assertEqual(result["physical_delivery_accounting_event"]["unknown_trials"], 1)
        for value in ("three", True, -1, 5):
            with self.subTest(distinct=value):
                snap = snapshot()
                snap["audit_after"]["distinct_completed_citizens"] = value
                self.assertIsNone(physical_delivery_accounting(snap))
                # Diagnostic parsing must not crash on malformed optional input.
                diagnostic_flags(snap)

    def test_additional_event_missing_and_invalid_worlds_retain_uncertainty(self):
        self.records[0] = record(PLAN[0], done=2, assigned=2)
        self.records[1]["artifact_validation_errors"] = ["retained log missing"]
        self.records[2].update(status="INFRASTRUCTURE_FAILURE", fixture_passed=False,
                               observation_window_completed=False, terminal_snapshot=None,
                               world={}, error_type="TimeoutError")
        result = summarize(self.records[:4])
        event = result["physical_delivery_accounting_event"]
        self.assertEqual((event["observed"], event["assessable_trials"],
                          event["unknown_trials"]), (1, 2, 3))
        self.assertEqual(event["planned_cohort_missingness_bounds"], [0.2, 0.8])
        self.assertEqual(event["wilson_95_interval_among_assessable"], wilson(1, 2))
        self.assertIsNone(result["trials"][-1]["physical_delivery_accounting_event_observed"])

    def test_additional_event_cannot_pool_invalid_cohorts(self):
        cohorts = [self.records + [copy.deepcopy(self.records[0])]]
        for field, value in (("source_commit", "c" * 40), ("protocol_sha256", "d" * 64)):
            records = copy.deepcopy(self.records)
            records[0][field] = value
            cohorts.append(records)
        for records in cohorts:
            result = summarize(records)
            event = result["physical_delivery_accounting_event"]
            self.assertEqual((event["observed"], event["assessable_trials"],
                              event["unknown_trials"]), (0, 0, 5))
            self.assertEqual(event["planned_cohort_missingness_bounds"], [0.0, 1.0])

    def test_missing_world_is_never_dropped(self):
        result = summarize(self.records[:4])
        self.assertEqual(result["planned_trials"], 5)
        self.assertFalse(result["all_trials_passed"])
        event = result["three_of_four_accounting_event"]
        self.assertEqual((event["assessable_trials"], event["unknown_trials"]), (4, 1))
        self.assertEqual(event["planned_cohort_missingness_bounds"], [0.0, 0.2])

    def test_boot_failure_is_unknown_not_zero_accounting_failures(self):
        failed = self.records[1]
        failed.update(status="INFRASTRUCTURE_FAILURE", fixture_passed=False,
                      observation_window_completed=False, terminal_snapshot=None,
                      world={}, error_type="TimeoutError")
        result = summarize(self.records)
        self.assertEqual(result["statuses"]["INFRASTRUCTURE_FAILURE"], 1)
        self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 1)

    def test_interrupted_result_is_retained_as_invalid(self):
        self.records[0]["status"] = "RUNNING"
        result = summarize(self.records)
        self.assertEqual(result["statuses"]["INVALID_EVIDENCE"], 1)
        self.assertFalse(result["all_trials_passed"])

    def test_duplicate_trial_invalidates_pooled_estimate(self):
        result = summarize(self.records + [copy.deepcopy(self.records[0])])
        self.assertFalse(result["all_trials_passed"])
        self.assertEqual(result["three_of_four_accounting_event"]["assessable_trials"], 0)
        self.assertIn("duplicate", result["cohort_errors"][0])

    def test_duplicate_world_uuid_cannot_count_twice(self):
        self.records[1]["world"]["world_uuid"] = self.records[0]["world"]["world_uuid"]
        result = summarize(self.records)
        self.assertFalse(result["all_trials_passed"])
        self.assertEqual(result["three_of_four_accounting_event"]["assessable_trials"], 4)
        self.assertIn("persisted world UUID reused", result["trials"][1]["errors"])

    def test_seed_rewrite_rejected(self):
        for field, value in (("generated_seed", 99), ("configured_seed", "legacy-fixed-seed")):
            records = copy.deepcopy(self.records)
            records[0]["world"][field] = value
            result = summarize(records)
            self.assertFalse(result["all_trials_passed"])
            self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 1)

    def test_mixed_revision_and_protocol_cannot_be_pooled(self):
        for field, value in (("source_commit", "c" * 40), ("protocol_sha256", "d" * 64)):
            records = copy.deepcopy(self.records)
            records[0][field] = value
            result = summarize(records)
            self.assertFalse(result["all_trials_passed"])
            self.assertEqual(result["three_of_four_accounting_event"]["assessable_trials"], 0)

    def test_wrong_requested_revision_rejected(self):
        result = summarize(self.records, expected_commit="f" * 40)
        self.assertEqual(result["statuses"], {"INVALID_EVIDENCE": 5})
        self.assertIsNone(result["three_of_four_accounting_event"]["frequency_among_assessable"])

    def test_pass_marker_without_physical_evidence_rejected(self):
        for key, value in (("destination_has_exact_four_wheat", False),
                           ("source_wheat_absent", [True, True, True, False]),
                           ("outstanding_claims", 1)):
            records = copy.deepcopy(self.records)
            records[0]["terminal_snapshot"][key] = value
            result = summarize(records)
            self.assertFalse(result["all_trials_passed"])
            self.assertEqual(result["statuses"]["INVALID_EVIDENCE"], 1)

    def test_malformed_nested_evidence_is_reported_not_crashed(self):
        for field in ("world", "terminal_snapshot"):
            records = copy.deepcopy(self.records)
            records[0][field] = None
            result = summarize(records)
            self.assertEqual(result["statuses"]["INVALID_EVIDENCE"], 1)
            self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 1)

    def test_pass_requires_complete_window_and_retained_logs(self):
        for field, value in (("observation_window_completed", False),
                             ("rcon_log_sha256", ""),
                             ("artifact_validation_errors", ["retained log missing: rcon.log"])):
            records = copy.deepcopy(self.records)
            records[0][field] = value
            result = summarize(records)
            self.assertFalse(result["all_trials_passed"])
            self.assertEqual(result["statuses"]["INVALID_EVIDENCE"], 1)

    def test_early_fixture_failure_remains_unknown(self):
        failed = self.records[0]
        failed.update(status="FIXTURE_ASSERTION_FAILURE", fixture_passed=False,
                      observation_window_completed=False, error_type="AssertionError")
        result = summarize(self.records)
        self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 1)

    def test_complete_failed_physical_trial_remains_in_denominator(self):
        failed = self.records[0]
        failed.update(status="FIXTURE_ASSERTION_FAILURE", fixture_passed=False,
                      error_type="AssertionError")
        failed["terminal_snapshot"]["destination_has_exact_four_wheat"] = False
        result = summarize(self.records)
        self.assertEqual(result["three_of_four_accounting_event"]["assessable_trials"], 5)
        self.assertFalse(result["all_trials_passed"])

    def test_reconciled_during_probe_does_not_assert_stable_three_of_four(self):
        snap = snapshot(3, 1)
        snap["audit_after"] = snapshot()["audit_after"]
        self.assertFalse(accounting_three_of_four(snap))
        self.assertEqual(classified_status(False, True, "AssertionError", snap),
                         "TASK_ACCOUNTING_MISMATCH")

    def test_physically_incomplete_is_not_accounting_signature(self):
        snap = snapshot(3, 1)
        snap["source_wheat_absent"][3] = False
        self.assertFalse(accounting_three_of_four(snap))
        self.assertEqual(classified_status(False, True, "AssertionError", snap),
                         "FIXTURE_ASSERTION_FAILURE")

    def test_empty_results_report_every_planned_trial(self):
        result = summarize([])
        self.assertEqual(result["statuses"], {"MISSING_RESULT": 5})
        self.assertEqual(result["three_of_four_accounting_event"]["planned_cohort_missingness_bounds"], [0.0, 1.0])

    def test_wilson_and_counters(self):
        self.assertIsNone(wilson(0, 0))
        self.assertAlmostEqual(wilson(0, 5)[1], 1 - wilson(5, 5)[0])
        with self.assertRaises(ValueError):
            wilson(6, 5)
        self.assertEqual(counters("prefix COLONY_V1 enabled=true assigned=1 done=3", "COLONY_V1"),
                         {"assigned": 1, "done": 3})


class ProspectivePlanTests(unittest.TestCase):
    def setUp(self):
        self.plans = [prospective_plan(item) for item in PLAN]
        self.records = [record(item) for item in PLAN]
        for result, document in zip(self.records, self.plans):
            self.bind(result, document)

    @staticmethod
    def bind(result, document):
        result.update(prospective_plan_required=True,
                      prospective_plan_sha256=plan_hash(document),
                      github_run_id=document["github_run_id"],
                      github_run_attempt=document["github_run_attempt"])

    def summarize(self, records=None, plans=None):
        return summarize(self.records if records is None else records,
                         prospective_plans=self.plans if plans is None else plans,
                         expected_commit=COMMIT, expected_protocol=HASH,
                         require_prospective_plans=True)

    def test_verified_plans_do_not_redefine_original_events(self):
        self.records[0] = record(PLAN[0], done=3, assigned=1)
        self.bind(self.records[0], self.plans[0])
        result = self.summarize()
        self.assertEqual(result["statuses"], {"ACCOUNTING_THREE_OF_FOUR": 1, "PASS": 4})
        self.assertEqual(result["three_of_four_accounting_event"]["frequency_among_assessable"], 0.2)
        self.assertEqual(result["prospective_plans"]["statuses"], {"VERIFIED": 5})
        self.assertTrue(result["prospective_plans"]["all_required_plans_verified"])
        self.assertTrue(result["post_window_motor_diagnostics"]["required_for_cohort"])

    def test_precompile_failure_is_unknown_with_a_plan_and_no_fabricated_world(self):
        result = self.summarize(records=self.records[:4])
        self.assertEqual(result["planned_trials"], 5)
        self.assertEqual(result["received_unique_trials"], 4)
        self.assertEqual(result["statuses"], {"NOT_RUN": 1, "PASS": 4})
        row = result["trials"][-1]
        self.assertEqual(row["prospective_plan"]["status"], "VERIFIED")
        self.assertNotIn("world_uuid", row)
        self.assertNotIn("terminal_snapshot", row)
        for key in ("three_of_four_accounting_event", "physical_delivery_accounting_event"):
            self.assertEqual(result[key]["unknown_trials"], 1)
            self.assertEqual(result[key]["planned_cohort_missingness_bounds"], [0.0, 0.2])
        self.assertFalse(result["all_trials_passed"])

    def test_all_builds_can_fail_without_any_negative_event_or_created_world(self):
        result = self.summarize(records=[])
        self.assertEqual(result["statuses"], {"NOT_RUN": 5})
        self.assertEqual(result["source_commits"], [COMMIT])
        self.assertEqual(result["protocol_hashes"], [HASH])
        event = result["three_of_four_accounting_event"]
        self.assertEqual((event["observed"], event["assessable_trials"], event["unknown_trials"]), (0, 0, 5))
        self.assertIsNone(event["frequency_among_assessable"])
        self.assertIsNone(event["wilson_95_interval_among_assessable"])

    def test_trusted_plan_gate_cannot_be_disabled_by_result_flags(self):
        for item in self.records:
            item["prospective_plan_required"] = False
        result = self.summarize(plans=[])
        self.assertEqual(result["statuses"], {"INVALID_EVIDENCE": 5})
        self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 5)
        self.assertEqual(result["prospective_plans"]["statuses"], {"MISSING": 5})

    def test_invalid_plan_never_promotes_an_observed_or_unstarted_world(self):
        changes = (
            ("schema", "other"), ("seed", 43102), ("source_commit", "f" * 40),
            ("protocol_sha256", "e" * 64), ("level_name", "reused-world"),
            ("declaration_phase", "AFTER_OUTCOME"), ("execution_policy", "RETRY_UNTIL_PASS"),
            ("fresh_world_required", False), ("motor_diagnostics_required", False),
            ("github_run_attempt", "0"), ("world_uuid", "invented-before-world-creation"),
            ("extra", float("nan")),
        )
        for field, value in changes:
            with self.subTest(field=field):
                plans = copy.deepcopy(self.plans)
                plans[0][field] = value
                result = self.summarize(plans=plans)
                self.assertEqual(result["statuses"], {"INVALID_EVIDENCE": 1, "PASS": 4})
                self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 1)
                self.assertFalse(result["prospective_plans"]["all_required_plans_verified"])
                missing = self.summarize(records=self.records[1:], plans=plans)
                self.assertEqual(missing["trials"][0]["status"], "INVALID_EVIDENCE")

    def test_result_must_bind_the_retained_plan_and_workflow_attempt(self):
        for field, value in (("prospective_plan_sha256", "c" * 64),
                             ("github_run_id", "999"), ("github_run_attempt", "2")):
            with self.subTest(field=field):
                records = copy.deepcopy(self.records)
                records[0][field] = value
                result = self.summarize(records=records)
                self.assertEqual(result["statuses"], {"INVALID_EVIDENCE": 1, "PASS": 4})
                self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 1)

    def test_duplicate_extra_and_mixed_attempt_plans_invalidate_cohort(self):
        for extra in (copy.deepcopy(self.plans[0]), {"trial_id": "unexpected-world"}):
            result = self.summarize(plans=self.plans + [extra])
            self.assertTrue(result["cohort_errors"])
            self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 5)
        for field, value in (("github_run_id", "999"), ("github_run_attempt", "2")):
            plans, records = copy.deepcopy(self.plans), copy.deepcopy(self.records)
            plans[0][field] = value
            self.bind(records[0], plans[0])
            result = self.summarize(records=records, plans=plans)
            self.assertIn("mixed prospective workflow runs or attempts", result["cohort_errors"])
            self.assertEqual(result["three_of_four_accounting_event"]["unknown_trials"], 5)


class DeclarationTests(unittest.TestCase):
    def test_exclusive_declaration_creates_no_world_and_preserves_first_plan(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict(os.environ, {"HEARTHBOUND_EXPECTED_COMMIT": COMMIT}, clear=True), \
                patch("run_colony_reliability_trial.subprocess.check_output", return_value=COMMIT), \
                patch("run_colony_reliability_trial.protocol_hash", return_value=HASH):
            root = Path(temporary)
            path = root / "declarations/trial-plan.json"
            document = declare(root, "world-01", 43101, path)
            self.assertEqual(document["source_commit"], COMMIT)
            self.assertFalse((root / "run").exists())
            self.assertNotIn("world", document)
            self.assertNotIn("world_uuid", document)
            original = path.read_bytes()
            with self.assertRaises(FileExistsError):
                declare(root, "world-01", 43101, path)
            self.assertEqual(path.read_bytes(), original)

    def test_wrong_commit_is_rejected_before_writing_a_plan(self):
        with tempfile.TemporaryDirectory() as temporary, \
                patch.dict(os.environ, {"HEARTHBOUND_EXPECTED_COMMIT": "f" * 40}, clear=True), \
                patch("run_colony_reliability_trial.subprocess.check_output", return_value=COMMIT):
            path = Path(temporary) / "trial-plan.json"
            with self.assertRaisesRegex(ValueError, "requested head"):
                declare(Path(temporary), "world-01", 43101, path)
            self.assertFalse(path.exists())

    def test_invalid_plan_blocks_server_start_without_fabricating_an_outcome(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ, {}, clear=True), \
                patch("run_colony_reliability_trial.subprocess.check_output", return_value=COMMIT), \
                patch("run_colony_reliability_trial.protocol_hash", return_value=HASH), \
                patch("run_colony_reliability_trial.subprocess.Popen") as process, \
                patch("builtins.print"):
            root = Path(temporary)
            document = prospective_plan(PLAN[0])
            document["source_commit"] = "e" * 40
            path = root / "trial-plan.json"
            path.write_text(json.dumps(document))
            result = run(root, "world-01", 43101, root / "result", plan_file=path)
            process.assert_not_called()
            self.assertFalse((root / "run").exists())
            self.assertFalse(result["observation_window_completed"])
            self.assertEqual(result["world"], {})
            self.assertIsNone(result["terminal_snapshot"])
            self.assertEqual(result["status"], "INFRASTRUCTURE_FAILURE")

    def test_build_configuration_and_helper_changes_alter_protocol_hash(self):
        build_inputs = (
            "build.gradle", "settings.gradle", "gradle.properties",
            "gradle/forge-build-environment.gradle", "gradle/force-forge-tool-fallback.init.gradle",
            "scripts/run_forge_build_preflight.py",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in PROTOCOL_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("synthetic protocol input " + name)
            original = protocol_hash(root)
            for name in build_inputs:
                with self.subTest(name=name):
                    path = root / name
                    saved = path.read_bytes()
                    path.write_bytes(saved + b" changed build input")
                    self.assertNotEqual(protocol_hash(root), original)
                    path.write_bytes(saved)


def nbt_string(text):
    encoded = text.encode()
    return struct.pack(">H", len(encoded)) + encoded


def nbt_named(kind, name, payload):
    return bytes([kind]) + nbt_string(name) + payload


def nbt_root(payload):
    return nbt_named(10, "", payload + b"\0")


class PersistenceTests(unittest.TestCase):
    def test_real_nbt_shape_yields_persisted_uuid_and_generated_seed(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            (path / "data").mkdir()
            identity = nbt_root(nbt_named(10, "data", nbt_named(
                8, "worldUuid", nbt_string("12345678-1234-1234-1234-123456789abc")) + b"\0"))
            level = nbt_root(nbt_named(10, "Data", nbt_named(10, "WorldGenSettings",
                nbt_named(4, "seed", struct.pack(">q", 43101)) + b"\0") + b"\0"))
            (path / "level.dat").write_bytes(gzip.compress(level))
            (path / "data/hearthbound_world_identity_v1.dat").write_bytes(gzip.compress(identity))
            evidence = world_evidence(path, "colony-reliability-world-01", 43101)
            self.assertEqual(evidence["generated_seed"], 43101)
            self.assertEqual(evidence["world_uuid"], "12345678-1234-1234-1234-123456789abc")
            with self.assertRaises(ValueError):
                world_evidence(path, "colony-reliability-world-01", 43102)

    def test_invalid_nbt_refused(self):
        for payload in (b"", b"\x08\0\0", nbt_root(b"") + b"garbage",
                        nbt_root(nbt_named(8, "field", b"\0\xffa"))):
            with self.assertRaises((ValueError, struct.error)):
                NbtReader(payload).root()


class ArtifactTests(unittest.TestCase):
    def test_cli_preserves_precompile_plans_and_rejects_an_unreadable_plan(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            protocol = protocol_hash(Path(__file__).resolve().parents[1])
            for item in PLAN:
                directory = path / item["trial_id"] / "plans"
                directory.mkdir(parents=True)
                document = prospective_plan(item)
                document["protocol_sha256"] = protocol
                (directory / "trial-plan.json").write_text(json.dumps(document))
            script = Path(__file__).with_name("summarize_colony_reliability.py")
            command = [sys.executable, str(script), str(path), "--expected-commit", COMMIT,
                       "--require-prospective-plans", "--require-motor-diagnostics",
                       "--output", str(path / "summary.json")]
            incomplete = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(incomplete.returncode, 1, incomplete.stderr)
            summary = json.loads((path / "summary.json").read_text())
            self.assertEqual(summary["statuses"], {"NOT_RUN": 5})
            self.assertEqual(summary["prospective_plans"]["statuses"], {"VERIFIED": 5})
            self.assertEqual(summary["three_of_four_accounting_event"]["unknown_trials"], 5)
            self.assertEqual(summary["post_window_motor_diagnostics"]["statuses"], {"MISSING_TRIAL": 5})
            (path / "world-01/plans/trial-plan.json").write_text("{truncated")
            unreadable = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(unreadable.returncode, 1, unreadable.stderr)
            summary = json.loads((path / "summary.json").read_text())
            self.assertFalse(summary["prospective_plans"]["all_required_plans_verified"])
            self.assertEqual(summary["three_of_four_accounting_event"]["unknown_trials"], 5)
            self.assertTrue(any("UNREADABLE" in error for error in summary["cohort_errors"]))

    def test_cli_checks_artifact_integrity_and_unreadable_extras(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            for item in PLAN:
                directory = path / item["trial_id"]
                (directory / "world-metadata").mkdir(parents=True)
                value = record(item)
                for name, key in (("rcon.log", "rcon_log_sha256"),
                                  ("forge-server.log", "server_log_sha256")):
                    payload = ("synthetic unit log " + name).encode()
                    (directory / name).write_bytes(payload)
                    value[key] = hashlib.sha256(payload).hexdigest()
                for name, key in (("level.dat", "level_dat_sha256"),
                                  ("hearthbound_world_identity_v1.dat", "world_identity_sha256")):
                    payload = ("synthetic unit metadata " + name).encode()
                    (directory / "world-metadata" / name).write_bytes(payload)
                    value["world"][key] = hashlib.sha256(payload).hexdigest()
                (directory / "trial-result.json").write_text(json.dumps(value))
            script = Path(__file__).with_name("summarize_colony_reliability.py")
            command = [sys.executable, str(script), str(path), "--expected-commit", COMMIT,
                       "--output", str(path / "summary.json")]
            success = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(success.returncode, 0, success.stderr)
            self.assertTrue(json.loads((path / "summary.json").read_text())["all_trials_passed"])
            (path / PLAN[0]["trial_id"] / "rcon.log").write_text("changed bytes")
            corrupted_log = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(corrupted_log.returncode, 1)
            summary = json.loads((path / "summary.json").read_text())
            self.assertEqual(summary["three_of_four_accounting_event"]["unknown_trials"], 1)
            (path / "extra").mkdir()
            (path / "extra/trial-result.json").write_text("{truncated")
            unreadable = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(unreadable.returncode, 1)
            summary = json.loads((path / "summary.json").read_text())
            self.assertEqual(summary["three_of_four_accounting_event"]["unknown_trials"], 5)
            self.assertIn("UNREADABLE", summary["cohort_errors"][0])


if __name__ == "__main__":
    unittest.main()
