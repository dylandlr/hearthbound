#!/usr/bin/env python3
"""Synthetic cohort contracts; runtime wire validation has its own test suite."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
from uuid import UUID

import colony_motor_diagnostics as diagnostics
from haul_motor_diagnostics import PREFIX
from summarize_colony_reliability import PLAN, summarize
from test_colony_reliability import record, snapshot as terminal_snapshot
from test_haul_motor_diagnostics import completed as completed_snapshot
from run_colony_reliability_trial import Rcon, TraceRetainingRcon

CITIZENS = [f"00000000-0000-0000-0000-{index:012d}" for index in range(1, 5)]
WORLD = "00000000-0000-0000-0000-000000043101"
JOB = "10000000-0000-0000-0000-000000000001"
JOBS = {citizen: f"10000000-0000-0000-0000-{index:012d}" for index, citizen in enumerate(CITIZENS, 1)}
EPISODE = "20000000-0000-0000-0000-000000000001"


def trace_wire():
    entries = [",".join(map(str, (index, citizen, JOBS[citizen],
                f"30000000-0000-0000-0000-{index:012d}",
                f"40000000-0000-0000-0000-{index:012d}", 1, 10, 10, 20, 90)))
               for index, citizen in enumerate(CITIZENS, 1)]
    return (diagnostics.TRACE_PREFIX + " count=4 episode=" + EPISODE
            + " scope=" + diagnostics.TRACE_SCOPE + " entries=" + ";".join(entries)
            + " learning_authorized=false reward_authorized=false\n")


def retained_wire(raw=None):
    return [{"command": diagnostics.TRACE_COMMAND, "request_id": 51,
             "response": trace_wire() if raw is None else raw}]


class TraceRcon:
    """Full native diagnostic wire replies; these tests use the real parser."""
    def __init__(self, nearby=None, states=None, native_replies=None, snapshot_change=None):
        self.nearby = CITIZENS if nearby is None else nearby
        self.states = states or {}
        self.native_replies = native_replies or {}
        self.snapshot_change = snapshot_change
        self.commands = []
        self.observations = {}

    def run(self, command):
        self.commands.append(command)
        if command.startswith("hearthbound-colony source-readiness-audit "):
            return roster(self.nearby, tuple(map(int, command.split()[-3:])))
        if command.startswith("hearthbound-haul-diagnostics "):
            citizen = command.split()[-1]
            index = self.observations.get(citizen, -1) + 1
            self.observations[citizen] = index
            value = completed_snapshot()
            value.update(citizen=citizen, world=WORLD, tick=200 + 20 * index)
            value["entity"].update(tick_count=100 + 20 * index)
            value["haul"].update(job=JOBS.get(citizen), world=WORLD)
            value["haul"]["types"]["colonyWorldId"] = 11
            state = self.states.get((citizen, index), "alive" if citizen in JOBS else "missing")
            if state == "missing":
                value = {key: item for key, item in value.items() if key not in (
                    "entity", "haul", "claim", "motor", "navigation", "inventories", "read_only_checks")}
                value.update(status="NOT_LOADED_IN_DIMENSION", loaded=False)
            elif state == "dead":
                value["entity"]["alive"] = False
            if self.snapshot_change:
                self.snapshot_change(value, citizen, index)
            return PREFIX + json.dumps(value, separators=(",", ":"))
        if command.startswith(("execute if data entity ", "data get entity ")):
            presence = command.startswith("execute ")
            citizen = command.split()[4 if presence else 3]
            field = command.rsplit(".", 1)[1]
            index = self.observations[citizen]
            override = self.native_replies.get((citizen, index, field, "presence" if presence else "data"))
            if override is not None:
                return override
            if self.states.get((citizen, index)) == "missing" or citizen not in JOBS:
                return "No entity was found\n"
            if presence:
                return "Test failed\n" if field == "cargo" else "Test passed, count: 1\n"
            value = ("[I; " + ", ".join(map(str, struct.unpack(">iiii", UUID(JOBS[citizen]).bytes))) + "]"
                     if field == "jobId" else "2")
            return "Sable has the following entity data: " + value + "\n"
        raise AssertionError("Unexpected observer command: " + command)


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
            log = "MULTI_CITIZEN_RCON id=50 command='hearthbound-colony audit' response='COLONY_V1'\n"
            (path.parent / "rcon.log").write_text(log)
            value["rcon_log_sha256"] = hashlib.sha256(log.encode()).hexdigest()
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


class RetainedRosterTests(unittest.TestCase):
    def capture(self, rcon=None, traces=None):
        terminal = terminal_snapshot(4, 0)
        frozen = copy.deepcopy(terminal)
        rcon = rcon or TraceRcon()
        report = diagnostics.capture(rcon, terminal, sleep=lambda _: None,
                                     retained_traces=retained_wire() if traces is None else traces)
        self.assertEqual(terminal, frozen)
        self.assertEqual(report["terminal_snapshot_before_sampling"], frozen)
        self.assertEqual(report["terminal_snapshot_sha256"], diagnostics.digest(frozen))
        self.assertNotIn(diagnostics.TRACE_COMMAND, rcon.commands)
        return report, {"terminal_snapshot": terminal, "world": {"world_uuid": WORLD}}, rcon

    def inspect_stored_report(self, report, value, log):
        value = copy.deepcopy(value)
        value["motor_diagnostics_required"] = True
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            payload = json.dumps(report).encode()
            (directory / diagnostics.FILENAME).write_bytes(payload)
            (directory / "rcon.log").write_text(log)
            value["motor_diagnostics"] = {"status": "COMPLETE", "file": diagnostics.FILENAME,
                                          "sha256": hashlib.sha256(payload).hexdigest()}
            value["rcon_log_sha256"] = hashlib.sha256(log.encode()).hexdigest()
            return diagnostics.inspect_artifact(directory, value, required=True)

    def test_four_retained_identities_survive_three_current_nearby_citizens(self):
        report, value, rcon = self.capture(TraceRcon(nearby=CITIZENS[1:]))
        self.assertEqual(report["status"], "COMPLETE")
        self.assertEqual(report["identity_source"], diagnostics.TRACE_IDENTITY)
        self.assertEqual(report["citizens"], CITIZENS)
        self.assertTrue(all(row["citizens"] == CITIZENS[1:] for row in report["roster_queries"]))
        self.assertEqual(rcon.observations, dict.fromkeys(CITIZENS, 2))
        checked = diagnostics.validate_report(report, value)
        self.assertEqual(checked["snapshots"], 12)
        self.assertEqual(checked["native_field_read_coverage"],
                         {"OBSERVED_NATIVE_VALUE": 16, "ABSENT_AT_NATIVE_PROBE": 8})
        retained = report["retained_trace_queries"][0]
        self.assertEqual(retained["response"], trace_wire())
        self.assertEqual(retained["response_sha256"], hashlib.sha256(trace_wire().encode()).hexdigest())

    def test_missing_trace_uses_only_declared_fallback_and_partial_coverage_stays_incomplete(self):
        complete, value, _ = self.capture(traces=[])
        self.assertEqual(complete["identity_source"], diagnostics.FALLBACK_IDENTITY)
        self.assertEqual(diagnostics.validate_report(complete, value)["status"], "VERIFIED_COMPLETE")
        partial, value, rcon = self.capture(TraceRcon(nearby=CITIZENS[1:]), traces=[])
        self.assertEqual(partial["status"], "INCOMPLETE")
        self.assertEqual(partial["expected_citizens"], 4)
        self.assertEqual(partial["citizens"], CITIZENS[1:])
        self.assertEqual(rcon.observations, dict.fromkeys(CITIZENS[1:], 2))
        self.assertEqual(sum(len(group["citizens"]) for group in partial["rounds"]), 9)
        with self.assertRaises(ValueError):
            diagnostics.validate_report(partial, value)

    def test_still_loaded_observed_dead_actor_is_valid_evidence(self):
        states = {(CITIZENS[0], index): "dead" for index in range(3)}
        report, value, _ = self.capture(TraceRcon(states=states))
        self.assertEqual(report["status"], "COMPLETE")
        self.assertTrue(all(group["citizens"][0]["snapshot"]["entity"]["alive"] is False
                            for group in report["rounds"]))
        self.assertEqual(diagnostics.validate_report(report, value)["status"], "VERIFIED_COMPLETE")

    def test_disappearing_first_actor_does_not_stop_survivors_or_later_rounds(self):
        states = {(CITIZENS[0], 0): "dead", (CITIZENS[0], 1): "missing", (CITIZENS[0], 2): "missing"}
        report, value, rcon = self.capture(TraceRcon(states=states))
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(rcon.observations, dict.fromkeys(CITIZENS, 2))
        self.assertEqual(len(report["rounds"]), 3)
        self.assertEqual(report["rounds"][0]["citizens"][0]["snapshot"]["entity"]["alive"], False)
        for group in report["rounds"][1:]:
            self.assertEqual(group["citizens"][0]["snapshot"]["status"], "NOT_LOADED_IN_DIMENSION")
            self.assertNotIn("haul", group["citizens"][0]["snapshot"])
            self.assertTrue(all(row["snapshot"]["status"] == "OBSERVED" for row in group["citizens"][1:]))
        witnesses = report["rounds"][2]["citizens"][0]["native_haul_witnesses"]
        self.assertEqual(set(witnesses), {"jobId", "phase", "cargo"})
        for field, witness in witnesses.items():
            self.assertEqual(witness["presence_response"], "No entity was found\n")
            self.assertIsNone(witness["data_command"])
            self.assertIsNone(witness["data_response"])
            self.assertIn("error", witness)
            with self.assertRaises(ValueError):
                diagnostics.validate_native_witness(witness, CITIZENS[0], field)
        self.assertEqual(len(report["errors"]), 5)  # two unavailable snapshots plus three native fields
        with self.assertRaises(ValueError):
            diagnostics.validate_report(report, value)

    def test_unavailable_native_presence_and_value_bytes_are_retained_before_validation(self):
        for kind in ("presence", "data"):
            with self.subTest(kind=kind):
                raw = "No entity was found\n"
                report, value, rcon = self.capture(TraceRcon(native_replies={
                    (CITIZENS[0], 0, "jobId", kind): raw}))
                self.assertEqual(report["status"], "INCOMPLETE")
                self.assertEqual(rcon.observations, dict.fromkeys(CITIZENS, 2))
                row = report["rounds"][0]["citizens"][0]
                witness = row["native_haul_witnesses"]["jobId"]
                self.assertEqual(witness[kind + "_response"], raw)
                self.assertEqual(set(row["native_haul_witnesses"]), {"jobId", "phase", "cargo"})
                # Clearing error labels cannot promote unavailable native bytes.
                promoted = copy.deepcopy(report)
                promoted.update(status="COMPLETE", errors=[])
                promoted["rounds"][0]["citizens"][0]["errors"] = []
                promoted["rounds"][0]["citizens"][0]["native_haul_witnesses"]["jobId"].pop("error")
                with self.assertRaises(ValueError):
                    diagnostics.validate_report(promoted, value)

    def test_malformed_snapshot_does_not_discard_other_citizens(self):
        def corrupt(value, citizen, index):
            if citizen == CITIZENS[0] and index == 0:
                value["entity"]["alive"] = "unknown"
        report, _, rcon = self.capture(TraceRcon(snapshot_change=corrupt))
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(rcon.observations, dict.fromkeys(CITIZENS, 2))
        first = report["rounds"][0]["citizens"][0]
        self.assertIn('"alive":"unknown"', first["response"])
        self.assertNotIn("snapshot", first)
        self.assertEqual(set(first["native_haul_witnesses"]), {"jobId", "phase", "cargo"})

    def test_present_invalid_trace_never_promotes_a_complete_fallback(self):
        raw = trace_wire().replace("reward_authorized=false", "reward_authorized=true")
        report, value, rcon = self.capture(traces=retained_wire(raw))
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertEqual(report["identity_source"], diagnostics.FALLBACK_IDENTITY)
        self.assertEqual(report["retained_trace_queries"][0]["response"], raw)
        self.assertEqual(rcon.observations, dict.fromkeys(CITIZENS, 2))
        with self.assertRaises(ValueError):
            diagnostics.validate_report(report, value)
        doubled, _, _ = self.capture(traces=retained_wire() * 2)
        self.assertEqual(doubled["status"], "INCOMPLETE")
        self.assertEqual(len(doubled["retained_trace_queries"]), 2)

    def test_trace_parser_rejects_changed_envelope_authority_and_numeric_contracts(self):
        wire = trace_wire()
        cases = [wire.replace("count=4", "count=3"),
                 wire + " count=4", wire + " world=" + WORLD,
                 wire.replace("learning_authorized=false", "learning_authorized=true"),
                 wire.replace("scope=" + diagnostics.TRACE_SCOPE, "scope=ALL_CITIZENS"),
                 wire.replace("episode=" + EPISODE, "episode=not-a-uuid"),
                 wire.replace(CITIZENS[0], "not-a-canonical-uuid"),
                 wire.replace(",1,10,10,20,90", ",0,10,10,20,90", 1),
                 wire.replace(",1,10,10,20,90", ",1,-1,10,20,90", 1),
                 wire.replace(",1,10,10,20,90", ",1,10,10,31,90", 1),
                 wire.replace(",1,10,10,20,90", ",1,10,10,20,19", 1),
                 wire.replace(",1,10,10,20,90", ",1,10,10,20,9223372036854775808", 1),
                 wire.replace(" entries=1,", " entries=01,"),
                 wire + " " * 4000]
        for raw in cases:
            with self.subTest(raw=raw[:80]), self.assertRaises(ValueError):
                diagnostics.trace_response(raw)

    def test_trace_parser_rejects_each_duplicate_identity_class(self):
        wire = trace_wire()
        before, entries = wire.split(" entries=", 1)
        encoded, after = entries.split(" learning_authorized=", 1)
        for field in (0, 1, 2, 3, 4):
            rows = [entry.split(",") for entry in encoded.split(";")]
            rows[1][field] = rows[0][field]
            raw = before + " entries=" + ";".join(",".join(row) for row in rows) + " learning_authorized=" + after
            with self.subTest(field=field), self.assertRaises(ValueError):
                diagnostics.trace_response(raw)

    def test_foreign_trace_subjects_jobs_and_snapshot_worlds_fail_binding(self):
        foreign = "50000000-0000-0000-0000-000000000001"
        report, _, _ = self.capture(traces=retained_wire(trace_wire().replace(CITIZENS[0], foreign)))
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertTrue(any("contamination" in error for error in report["errors"]))
        report, _, _ = self.capture(traces=retained_wire(trace_wire().replace(JOBS[CITIZENS[0]], foreign)))
        self.assertEqual(report["status"], "INCOMPLETE")
        self.assertTrue(any("citizen/job chronology" in error for error in report["errors"]))
        def foreign_world(value, citizen, index):
            if citizen == CITIZENS[0]:
                value["haul"]["world"] = foreign
        report, _, _ = self.capture(TraceRcon(snapshot_change=foreign_world))
        self.assertEqual(report["status"], "INCOMPLETE")

    def test_trace_digest_source_projection_and_identity_authority_are_revalidated(self):
        report, value, _ = self.capture()
        for key, replacement in (("response_sha256", "0" * 64), ("source", "FRESH_REDISCOVERY"),
                                 ("command", "hearthbound-colony audit"), ("request_id", True),
                                 ("trace", {})):
            bad = copy.deepcopy(report)
            bad["retained_trace_queries"][0][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                diagnostics.validate_report(bad, value)
        report["identity_source"] = diagnostics.FALLBACK_IDENTITY
        with self.assertRaises(ValueError):
            diagnostics.validate_report(report, value)

    def test_retained_trace_artifact_must_match_its_hashed_original_rcon_exchange(self):
        report, value, _ = self.capture()
        value["motor_diagnostics_required"] = True
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            payload = json.dumps(report).encode()
            (directory / diagnostics.FILENAME).write_bytes(payload)
            value["motor_diagnostics"] = {"status": "COMPLETE", "file": diagnostics.FILENAME,
                                          "sha256": hashlib.sha256(payload).hexdigest()}
            trace = report["retained_trace_queries"][0]
            line = ("MULTI_CITIZEN_RCON id=" + str(trace["request_id"]) + " command="
                    + repr(trace["command"]) + " response=" + repr(trace["response"]) + "\n")
            for text, expected in ((line, "VERIFIED_COMPLETE"), (line * 2, "INVALID_DIAGNOSTIC_EVIDENCE"),
                                   (line.replace("id=51", "id=52"), "INVALID_DIAGNOSTIC_EVIDENCE"),
                                   (line + line.replace("id=51", "id=52"), "INVALID_DIAGNOSTIC_EVIDENCE")):
                (directory / "rcon.log").write_text(text)
                value["rcon_log_sha256"] = hashlib.sha256(text.encode()).hexdigest()
                checked = diagnostics.inspect_artifact(directory, value, required=True)
                self.assertEqual(checked["status"], expected)
            value["rcon_log_sha256"] = "0" * 64
            self.assertEqual(diagnostics.inspect_artifact(directory, value, required=True)["status"],
                             "INVALID_DIAGNOSTIC_EVIDENCE")

    def test_stripping_valid_or_malformed_trace_cannot_claim_fallback_absence(self):
        for malformed in (False, True):
            with self.subTest(malformed=malformed):
                raw = trace_wire()
                if malformed:
                    raw = raw.replace("reward_authorized=false", "reward_authorized=true")
                report, value, _ = self.capture(traces=retained_wire(raw))
                self.assertEqual(report["status"], "INCOMPLETE" if malformed else "COMPLETE")
                promoted = copy.deepcopy(report)
                promoted.update(status="COMPLETE", errors=[], retained_trace_queries=[],
                                identity_source=diagnostics.FALLBACK_IDENTITY)
                line = ("MULTI_CITIZEN_RCON id=51 command=" + repr(diagnostics.TRACE_COMMAND)
                        + " response=" + repr(raw) + "\n")
                checked = self.inspect_stored_report(promoted, value, line)
                self.assertEqual(checked["status"], "INVALID_DIAGNOSTIC_EVIDENCE")
                self.assertIn("complete original RCON trace-command set", checked["error"])

    def test_genuine_no_trace_fallback_proves_absence_in_hashed_source_log(self):
        report, value, _ = self.capture(traces=[])
        # Mentioning the trace in an unrelated reply is not issuing its command.
        log = ("MULTI_CITIZEN_RCON id=50 command='hearthbound-colony audit' response="
               + repr("unrelated reply mentioning " + diagnostics.TRACE_COMMAND) + "\n")
        checked = self.inspect_stored_report(report, value, log)
        self.assertEqual(checked["status"], "VERIFIED_COMPLETE")
        self.assertEqual(checked["identity_source"], diagnostics.FALLBACK_IDENTITY)
        self.assertTrue(checked["retained_trace_source_log_verified"])

    def test_malformed_source_trace_record_cannot_be_silently_treated_as_absent(self):
        report, value, _ = self.capture(traces=[])
        prefix = "MULTI_CITIZEN_RCON id=51 command=" + repr(diagnostics.TRACE_COMMAND)
        for log in (prefix + " reply='unrecognized source field'\n",
                    prefix + " response='unterminated string\n",
                    prefix.replace("id=51", "id=invalid") + " response='raw'\n"):
            with self.subTest(log=log):
                checked = self.inspect_stored_report(report, value, log)
                self.assertEqual(checked["status"], "INVALID_DIAGNOSTIC_EVIDENCE")
                self.assertIn("Malformed original decision-trace", checked["error"])


class TransparentTraceRecorderTests(unittest.TestCase):
    def test_records_existing_exact_command_once_and_returns_unchanged_response(self):
        rcon = TraceRetainingRcon(None)
        calls = []
        response = "malformed trace response preserved without parsing\n"
        def original_run(client, command):
            calls.append(command)
            client.next_id += 1
            return response
        commands = ["hearthbound-colony audit", diagnostics.TRACE_COMMAND,
                    diagnostics.TRACE_COMMAND + " unexpected-argument", "hearthbound-colony disable"]
        with patch.object(Rcon, "run", original_run):
            for command in commands:
                self.assertIs(rcon.run(command), response)
        self.assertEqual(calls, commands)
        self.assertEqual(rcon.retained_decision_traces, [{"command": diagnostics.TRACE_COMMAND,
                                                       "request_id": 21, "response": response}])

    def test_underlying_exception_propagates_without_retry_or_invented_response(self):
        rcon = TraceRetainingRcon(None)
        failure = ConnectionError("connection closed")
        with patch.object(Rcon, "run", side_effect=failure) as original:
            with self.assertRaises(ConnectionError) as caught:
                rcon.run(diagnostics.TRACE_COMMAND)
        self.assertIs(caught.exception, failure)
        original.assert_called_once_with(diagnostics.TRACE_COMMAND)
        self.assertEqual(rcon.retained_decision_traces, [])


if __name__ == "__main__":
    unittest.main()
