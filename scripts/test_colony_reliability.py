#!/usr/bin/env python3
"""Meaningful failure/provenance checks without fabricating Minecraft trials."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from run_colony_reliability_trial import NbtReader, world_evidence
from summarize_colony_reliability import (
    PLAN, TRIAL_SCHEMA, accounting_three_of_four, classified_status,
    counters, diagnostic_flags, summarize, wilson,
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
