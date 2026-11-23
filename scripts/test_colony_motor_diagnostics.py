#!/usr/bin/env python3
"""Synthetic cohort contracts; runtime wire validation has its own test suite."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import colony_motor_diagnostics as diagnostics
from haul_motor_diagnostics import PREFIX
from summarize_colony_reliability import PLAN, summarize
from test_colony_reliability import record, snapshot as terminal_snapshot

CITIZENS = [f"00000000-0000-0000-0000-{index:012d}" for index in range(1, 5)]
WORLD = "00000000-0000-0000-0000-000000043101"
JOB = "10000000-0000-0000-0000-000000000001"


def sample(citizen, game_tick, entity_tick, ticking=False, phase=1):
    return {"status": "OBSERVED", "citizen": citizen, "world": WORLD, "world_state": "PRESENT",
            "dimension": "minecraft:overworld", "tick": game_tick,
            "entity": {"position_entity_ticking": ticking, "tick_count": entity_tick,
                       "no_ai": False, "can_update": True},
            "motor": {"active": phase != 2, "paused": phase == 3, "quarantined": phase == 4,
                      "within_reach": False},
            "haul": {"job": JOB, "phase": phase, "cargo": {"present": phase != 2}},
            "claim": {"owned_by_citizen": phase != 2}, "navigation": {"done": True}}


def parse_for_cohort_test(response, citizen=None, expected_world=None, expected_dimension=None):
    value = json.loads(response[len(PREFIX):])
    if citizen is not None and value["citizen"] != citizen:
        raise ValueError("Foreign citizen")
    if expected_world is not None and value["world"] != expected_world:
        raise ValueError("Foreign world")
    return value


def roster(citizens=CITIZENS, source=(4, 100, 1)):
    return ("COLONY_SOURCE_READINESS_V0_9 source=" + ",".join(map(str, source))
            + " source_chunk_loaded=true citizens=" + str(len(citizens))
            + " truncated=false " + " ".join(f"citizen_{i}={value},pos:16:101:-1"
                                              for i, value in enumerate(citizens))
            + " strictly_read_only=true policy_control=false reward_authorized=false")


class FakeRcon:
    def __init__(self, later_complete=False):
        self.commands = []
        self.samples = 0
        self.later_complete = later_complete
        self.current_phase = 1

    def run(self, command):
        self.commands.append(command)
        if command.startswith("hearthbound-colony source-readiness-audit"):
            return roster(source=tuple(map(int, command.split()[-3:])))
        if command.startswith("hearthbound-haul-diagnostics"):
            citizen = command.split()[-1]
            round_index = self.samples // 4
            self.samples += 1
            phase = 2 if self.later_complete and round_index == 2 else 1
            self.current_phase = phase
            return PREFIX + json.dumps(sample(citizen, 2000 + round_index * 20, 50, phase=phase))
        if command.startswith("execute if data entity"):
            return "Test failed" if command.endswith(".cargo") and self.current_phase == 2 else "Test passed, count: 1"
        if command.startswith("data get entity"):
            value = ("[I; 268435456, 0, 0, 1]" if command.endswith(".jobId")
                     else str(self.current_phase) if command.endswith(".phase")
                     else '{id: "minecraft:wheat", Count: 1b}')
            return "Sable has the following entity data: " + value + "\n"
        raise AssertionError("Unexpected intervention: " + command)


class PostWindowTests(unittest.TestCase):
    def capture(self, later_complete=False):
        terminal = terminal_snapshot(3, 1)
        terminal["destination_has_exact_four_wheat"] = False
        terminal["outstanding_claims"] = 1
        rcon = FakeRcon(later_complete)
        with patch.object(diagnostics, "parse_snapshot", parse_for_cohort_test):
            report = diagnostics.capture(rcon, terminal, sleep=lambda _: None)
        return report, terminal, rcon

    def test_loaded_non_ticking_requires_advancing_world_and_static_entity(self):
        report, _, _ = self.capture()
        self.assertEqual(report["status"], "COMPLETE")
        for finding in report["findings"]:
            self.assertEqual(finding["game_tick_delta"], 40)
            self.assertEqual(finding["entity_tick_delta"], 0)
            self.assertIn("LOADED_NON_TICKING_SEQUENCE_OBSERVED", finding["flags"])
            self.assertFalse(finding["root_cause_established"])
        for group in report["rounds"]:
            for row in group["citizens"]:
                row["snapshot"]["tick"] = 2000
        self.assertTrue(all("LOADED_NON_TICKING_SEQUENCE_OBSERVED" not in f["flags"]
                            for f in diagnostics.sequence_findings(report)))

    def test_eligibility_does_not_prove_actor_executed(self):
        report, _, _ = self.capture()
        for group in report["rounds"]:
            for row in group["citizens"]:
                row["snapshot"]["entity"]["position_entity_ticking"] = True
        for finding in diagnostics.sequence_findings(report):
            self.assertIn("ENTITY_TICK_COUNT_UNCHANGED_WHILE_WORLD_ADVANCED", finding["flags"])
            self.assertNotIn("LOADED_NON_TICKING_SEQUENCE_OBSERVED", finding["flags"])

    def test_late_completion_never_rewrites_original_score(self):
        report, terminal, rcon = self.capture(later_complete=True)
        self.assertEqual(report["terminal_snapshot_before_sampling"], terminal)
        self.assertEqual(terminal["audit_after"]["done"], 3)
        self.assertFalse(terminal["destination_has_exact_four_wheat"])
        self.assertFalse(report["score_recomputed"])
        self.assertTrue(all("JOB_COMPLETED_DURING_POST_WINDOW_SAMPLING" in f["flags"]
                            for f in report["findings"]))
        self.assertFalse(any(word in command for command in rcon.commands
                             for word in ("forceload", "teleport", "summon", "haul-resume", "enable")))

    def test_unloaded_samples_are_not_interpreted_as_completion_or_zero_work(self):
        report, _, _ = self.capture()
        for group in report["rounds"]:
            for row in group["citizens"]:
                row["snapshot"] = {"status": "NOT_LOADED_IN_DIMENSION"}
        for finding in diagnostics.sequence_findings(report):
            self.assertEqual(finding["observed_samples"], 0)
            self.assertIsNone(finding["entity_tick_delta"])
            self.assertEqual(finding["flags"], [])

    def test_roster_rejects_truncation_duplicates_and_injection(self):
        for response in (roster().replace("truncated=false", "truncated=true"),
                         roster(CITIZENS[:3] + CITIZENS[:1]),
                         roster().replace("citizen_2=", "citizen_7="),
                         roster().replace("citizens=4", "citizens=3")):
            with self.subTest(response=response), self.assertRaises(ValueError):
                diagnostics.roster_response(response)
        with self.assertRaises(ValueError):
            diagnostics.command_for(CITIZENS[0] + " run kill @e")
        with self.assertRaises(ValueError):
            diagnostics.roster_response(roster(source=(12, 100, 1)), [4, 100, 1])
        with self.assertRaises(ValueError):
            diagnostics.roster_response(roster() + " policy_control=true", [4, 100, 1])

    def test_native_witness_requires_exact_command_and_recognizable_nbt(self):
        witness = diagnostics.native_witness(FakeRcon(), CITIZENS[0], "jobId")
        self.assertEqual(diagnostics.validate_native_witness(witness, CITIZENS[0], "jobId")["value"], JOB)
        for field, value in (("data_response", "No entity was found"),
                             ("presence_response", "Test failed due to an unrelated error"),
                             ("data_command", diagnostics.native_commands(CITIZENS[1], "jobId")[1]),
                             ("data_response", "Sable has the following entity data: [I; 1, 2, 3]")):
            bad = copy.deepcopy(witness)
            bad[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                diagnostics.validate_native_witness(bad, CITIZENS[0], "jobId")
        absent = FakeRcon()
        absent.current_phase = 2
        observed = diagnostics.native_witness(absent, CITIZENS[0], "cargo")
        self.assertEqual(diagnostics.validate_native_witness(observed, CITIZENS[0], "cargo")["status"],
                         "ABSENT_AT_NATIVE_PROBE")

    def test_trusted_requirement_cannot_be_disabled_by_artifact_flags(self):
        values = [record(item) for item in PLAN]
        for value in values:
            value["motor_diagnostics_required"] = False
        summary = summarize(values, require_motor_diagnostics=True)
        self.assertTrue(summary["all_trials_passed"])
        self.assertTrue(summary["post_window_motor_diagnostics"]["required_for_cohort"])
        self.assertFalse(summary["post_window_motor_diagnostics"]["all_required_worlds_verified"])
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(diagnostics.inspect_artifact(temporary, values[0], required=True)["status"],
                             "UNAVAILABLE")

    def test_invalid_world_provenance_cannot_enter_diagnostic_totals(self):
        value = record(PLAN[0])
        value["motor_diagnostics_required"] = True
        value["artifact_validation_errors"] = ["retained log hash mismatch"]
        value["verified_motor_diagnostics"] = {
            "status": "VERIFIED_COMPLETE", "findings": [{"flags": ["LOADED_NON_TICKING_SEQUENCE_OBSERVED"]}]}
        summary = summarize([value], plan=PLAN[:1], require_motor_diagnostics=True)
        self.assertEqual(summary["post_window_motor_diagnostics"]["citizen_sequence_patterns"], {})
        self.assertFalse(summary["post_window_motor_diagnostics"]["all_required_worlds_verified"])
        self.assertEqual(summary["trials"][0]["motor_diagnostics"]["status"], "INVALID_WORLD_PROVENANCE")

    def test_unavailable_claim_is_not_a_mismatching_owner(self):
        report, _, _ = self.capture()
        for group in report["rounds"]:
            for row in group["citizens"]:
                row["snapshot"]["claim"]["owned_by_citizen"] = None
        for finding in diagnostics.sequence_findings(report):
            self.assertIn("ACTIVE_JOB_SOURCE_OWNER_UNAVAILABLE_AT_LAST_SAMPLE", finding["flags"])
            self.assertNotIn("ACTIVE_JOB_WITHOUT_MATCHING_SOURCE_OWNER_AT_LAST_SAMPLE", finding["flags"])

    def test_report_binds_world_subject_and_frozen_terminal_snapshot(self):
        report, terminal, _ = self.capture()
        value = {"terminal_snapshot": terminal, "world": {"world_uuid": WORLD}}
        with patch.object(diagnostics, "parse_snapshot", parse_for_cohort_test):
            self.assertEqual(diagnostics.validate_report(report, value)["snapshots"], 12)
            bad = copy.deepcopy(report)
            bad["terminal_snapshot_before_sampling"]["audit_after"]["done"] = 4
            with self.assertRaises(ValueError):
                diagnostics.validate_report(bad, value)
            foreign = copy.deepcopy(value)
            foreign["world"]["world_uuid"] = CITIZENS[0]
            with self.assertRaises(ValueError):
                diagnostics.validate_report(report, foreign)
            missing = copy.deepcopy(report)
            missing["rounds"][1]["citizens"].pop()
            with self.assertRaises(ValueError):
                diagnostics.validate_report(missing, value)

    def test_diagnostic_corruption_fails_its_gate_without_changing_accounting_event(self):
        report, terminal, _ = self.capture()
        value = record(PLAN[0])
        value.update(motor_diagnostics_required=True, terminal_snapshot=terminal,
                     fixture_passed=False, error_type="AssertionError", status="FIXTURE_ASSERTION_FAILURE")
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / diagnostics.FILENAME
            payload = json.dumps(report).encode()
            path.write_bytes(payload)
            value["motor_diagnostics"] = {"status": "COMPLETE", "file": diagnostics.FILENAME,
                                          "sha256": hashlib.sha256(payload).hexdigest()}
            with patch.object(diagnostics, "parse_snapshot", parse_for_cohort_test):
                value["verified_motor_diagnostics"] = diagnostics.inspect_artifact(path.parent, value)
            original = summarize([value], plan=PLAN[:1])
            self.assertEqual(value["verified_motor_diagnostics"]["status"], "VERIFIED_COMPLETE")
            path.write_text("changed diagnostic bytes")
            value["verified_motor_diagnostics"] = diagnostics.inspect_artifact(path.parent, value)
            damaged = summarize([value], plan=PLAN[:1])
            self.assertEqual(damaged["three_of_four_accounting_event"], original["three_of_four_accounting_event"])
            self.assertEqual(damaged["statuses"], {"FIXTURE_ASSERTION_FAILURE": 1})
            self.assertFalse(damaged["post_window_motor_diagnostics"]["all_required_worlds_verified"])
            self.assertEqual(value["verified_motor_diagnostics"]["status"], "INVALID_DIAGNOSTIC_EVIDENCE")

    def test_incomplete_capture_retains_digest_and_planned_citizens(self):
        report, terminal, _ = self.capture()
        report["status"] = "INCOMPLETE"
        report["errors"] = ["Synthetic interrupted collection"]
        report["rounds"].pop()
        with tempfile.TemporaryDirectory() as temporary:
            payload = json.dumps(report).encode()
            path = Path(temporary) / diagnostics.FILENAME
            path.write_bytes(payload)
            value = {"motor_diagnostics_required": True,
                     "motor_diagnostics": {"status": "INCOMPLETE", "file": diagnostics.FILENAME,
                                           "sha256": hashlib.sha256(payload).hexdigest()},
                     "terminal_snapshot": terminal}
            checked = diagnostics.inspect_artifact(path.parent, value)
            self.assertEqual(checked["status"], "CAPTURE_INCOMPLETE")
            self.assertTrue(checked["artifact_digest_verified"])
            self.assertEqual(report["expected_citizens"], 4)
            self.assertEqual(report["planned_rounds"], 3)


if __name__ == "__main__":
    unittest.main()
