#!/usr/bin/env python3
"""Adversarial evidence tests; Minecraft pathfinding is checked by the live fixture."""
import copy
import json
from pathlib import Path
import struct
import unittest
from unittest.mock import patch
from uuid import UUID

from haul_motor_diagnostics import (
    PREFIX, SCHEMA, MAX_RESPONSE_BYTES, READ_ONLY_CHECKS, authority_view, command_for,
    parse_snapshot, require_blocked_cargo, require_completed, validate_snapshot,
)
from rcon_haul_motor_diagnostics import native_uuid
import rcon_haul_motor_diagnostics as fixture

CITIZEN = "11111111-1111-4111-8111-111111111111"
OTHER = "22222222-2222-4222-8222-222222222222"
WORLD = "33333333-3333-4333-8333-333333333333"
JOB = "44444444-4444-4444-8444-444444444444"
SOURCE, DESTINATION = [11, 100, 1], [7, 100, 1]


def inventory(wheat):
    return {"status": "OBSERVED", "scope": "LOCAL_VANILLA_CONTAINER_NBT", "slots": 27,
            "inspected_slots": 27, "wheat": wheat, "total_items": wheat, "complete": True}


def observed():
    return {
        "schema": SCHEMA, "status": "OBSERVED", "world": WORLD, "world_state": "PRESENT",
        "dimension": "minecraft:overworld", "dimension_available": True, "tick": 100,
        "citizen": CITIZEN, "loaded": True, "strictly_read_only": True, "atomic": True,
        "policy_control": False, "reward_authorized": False,
        "observation_scope": "NAMED_MOTOR_AUTHORITY_INVARIANTS",
        "invariant_baseline": "AFTER_NATIVE_ENTITY_SERIALIZATION",
        "entity": {"alive": True, "no_ai": False, "can_update": True, "tick_count": 80,
                   "position": [10.5, 100.0, 1.5], "velocity": [0.0, 0.0, 0.0], "on_ground": True,
                   "horizontal_collision": True, "chunk": [0, 0], "chunk_loaded": True,
                   "forced_chunk": True, "position_entity_ticking": True, "sable_marker": True,
                   "citizen_marker": False, "private_trial_marker": False},
        "haul": {"present": True, "type": 10,
                 "types": {"phase": 3, "source": 4, "destination": 4, "jobId": 11,
                           "colonyWorldId": 0, "assignedTick": 4, "physicalDeliveredTick": 0,
                           "cargo": 10, "error": 0},
                 "phase": 1, "phase_name": "TO_DEST", "job": JOB, "world": None,
                 "source": SOURCE.copy(), "destination": DESTINATION.copy(), "assigned_tick": 20,
                 "delivered_tick": None, "error": None, "error_truncated": False,
                 "cargo": {"present": True, "type": 10, "item": "minecraft:wheat", "count": 1,
                           "empty": False, "item_truncated": False}},
        "claim": {"store_present": True, "source_owner": CITIZEN, "owned_by_citizen": True,
                  "total_claims": 1},
        "motor": {"active": True, "phase_known": True, "paused": False, "quarantined": False,
                  "intended_target": DESTINATION.copy(), "reach_sq": 6.25, "target_chunk_loaded": True,
                  "distance_target": [7.5, 100.5, 1.5], "navigation_request_target": [7.5, 100, 1.5],
                  "distance_sq": 9.25, "within_reach": False},
        "navigation": {"done": True, "stuck": False, "target": DESTINATION.copy(),
                       "path_present": True, "next_node_index": 1, "node_count": 1,
                       "path_can_reach": False, "path_target": DESTINATION.copy(),
                       "next_node": None, "end_node": [10, 100, 1]},
        "inventories": {"source": inventory(7), "destination": inventory(0)},
        "read_only_checks": dict.fromkeys(READ_ONLY_CHECKS, True),
    }


def completed():
    value = observed()
    value["haul"].update(phase=2, phase_name="COMPLETE", delivered_tick=90)
    value["haul"]["types"].update(physicalDeliveredTick=4, cargo=0)
    value["haul"]["cargo"].update(present=False, type=0, item=None, count=None, empty=None)
    value["claim"].update(source_owner=None, owned_by_citizen=False, total_claims=0)
    value["motor"].update(active=False, intended_target=None, target_chunk_loaded=None, distance_target=None,
                          navigation_request_target=None, distance_sq=None, within_reach=None)
    value["inventories"]["destination"] = inventory(1)
    return value


def missing_probe(status="NOT_LOADED_IN_DIMENSION"):
    value = {key: val for key, val in observed().items()
             if key not in ("entity", "haul", "claim", "motor", "navigation", "inventories", "read_only_checks")}
    value.update(citizen=fixture.PROBE_CITIZEN, status=status, loaded=status != "NOT_LOADED_IN_DIMENSION")
    return value


def probe_snapshot(tick=100, entity_tick=10, forced=True, ticking=True):
    value = completed()
    value.update(citizen=fixture.PROBE_CITIZEN, tick=tick)
    value["entity"].update(no_ai=True, tick_count=entity_tick, position=list(fixture.PROBE_POSITION),
                           chunk=list(fixture.PROBE_CHUNK), forced_chunk=forced,
                           position_entity_ticking=ticking, horizontal_collision=False)
    value["haul"].update(present=False, type=0, phase=None, phase_name="ABSENT", job=None,
                         source=None, destination=None, assigned_tick=None, delivered_tick=None)
    value["haul"]["types"] = dict.fromkeys(value["haul"]["types"], 0)
    value["claim"].update(owned_by_citizen=None)
    value["motor"].update(phase_known=False)
    value["navigation"].update(target=None, path_present=False, next_node_index=None, node_count=None,
                                path_can_reach=None, path_target=None, next_node=None, end_node=None)
    value["inventories"] = {key: {"status": "NO_ENDPOINT", "scope": "LOCAL_VANILLA_CONTAINER_NBT",
                                 "slots": None, "inspected_slots": None, "wheat": None,
                                 "total_items": None, "complete": False}
                            for key in ("source", "destination")}
    return value


def probe_sequence(readiness=None):
    return [missing_probe(), missing_probe(), *(readiness or [probe_snapshot()]),
            probe_snapshot(200, 12, False, False), probe_snapshot(240, 12, False, False),
            probe_snapshot(280, 12, False, False), probe_snapshot(300, 13)]


class ProbeRcon:
    """Scripted transport replies exercise the real parser and fixture gates."""
    def __init__(self, probe_replies, native_identity=None, after_changes=None):
        self.probe_replies = list(probe_replies)
        self.native_identity = native_identity or fixture.PROBE_CITIZEN
        self.after_changes = after_changes or {}
        self.commands = []
        self.original_reads = {CITIZEN: 0, OTHER: 0}

    def run(self, command):
        self.commands.append(command)
        if command.startswith("hearthbound-haul-diagnostics "):
            citizen = command.split()[-1]
            if citizen in self.original_reads:
                self.original_reads[citizen] += 1
                value = completed()
                value["citizen"] = citizen
                if citizen == OTHER:
                    value["haul"]["job"] = OTHER
                if self.original_reads[citizen] > 1:
                    value["tick"] += 200
                    value["entity"]["tick_count"] += 200
                    value["entity"]["position"][0] += 0.25
                    value["navigation"]["stuck"] = True
                    change = self.after_changes.get(citizen)
                    if isinstance(change, Exception):
                        raise change
                    if change is not None:
                        change(value)
            else:
                assert citizen == fixture.PROBE_CITIZEN, command
                assert self.probe_replies, "Unexpected extra probe observation"
                value = copy.deepcopy(self.probe_replies.pop(0))
            return PREFIX + json.dumps(value, separators=(",", ":"))
        if command == f"data get entity {fixture.PROBE_CITIZEN} UUID":
            return "Probe has the following entity data: [I; " + ", ".join(
                map(str, struct.unpack(">iiii", UUID(self.native_identity).bytes))) + "]"
        if command.startswith("forceload "):
            return "Marked or unmarked chunk to be force loaded"
        if command.startswith("fill "):
            return "Successfully filled blocks"
        if command.startswith("summon minecraft:villager "):
            return "Summoned new HaulMotorChunkProbe"
        raise AssertionError("Unexpected or unsafe probe command: " + command)

    def require(self, command, expected):
        response = self.run(command)
        assert expected.lower() in response.lower(), (command, response)
        return response


class ChunkProbeIdentityTests(unittest.TestCase):
    def data(self):
        return {"citizens": {"A": CITIZEN, "B": OTHER}}

    def assert_no_fallback(self, rcon, removed=False):
        self.assertFalse(any("@e" in c or "sort=nearest" in c or c.startswith("data merge entity ")
                             for c in rcon.commands))
        if not removed:
            self.assertFalse(any(c.startswith("forceload remove ") for c in rcon.commands))

    def test_delayed_visibility_uses_exact_uuid_then_preserves_originals(self):
        readiness = [missing_probe(), missing_probe(), probe_snapshot(forced=False, ticking=False),
                     probe_snapshot(ticking=False), probe_snapshot()]
        rcon, data, sleeps = ProbeRcon(probe_sequence(readiness)), self.data(), []
        fixture.run_chunk_probe(rcon, data, sleeps.append)
        self.assert_no_fallback(rcon, removed=True)
        self.assertEqual(sleeps, [fixture.PROBE_POLL_SECONDS] * 4)
        self.assertEqual(data["probe_identity"]["readiness"]["polls"], 5)
        self.assertTrue(data["probe_identity"]["readiness"]["ready"])
        self.assertEqual(native_uuid(data["probe_identity"]["native_uuid_response"]), fixture.PROBE_CITIZEN)
        summons = [c for c in rcon.commands if c.startswith("summon ")]
        self.assertEqual(len(summons), 1)
        self.assertEqual(native_uuid(summons[0]), fixture.PROBE_CITIZEN)
        for nbt in ('PersistenceRequired:1b', 'NoAI:1b', 'ForgeData:{"hearthbound.sable":1b}'):
            self.assertIn(nbt, summons[0])
        binding = rcon.commands.index(f"data get entity {fixture.PROBE_CITIZEN} UUID")
        removal = rcon.commands.index(f"forceload remove {fixture.PROBE_COLUMN[0]} {fixture.PROBE_COLUMN[1]}")
        self.assertLess(binding, removal)
        self.assertEqual(len(data["chunk_suspended_reads"]), 3)
        self.assertEqual([s["tick"] for s in data["chunk_suspended_reads"]], [200, 240, 280])
        self.assertEqual(data["chunk_resumed"]["entity"]["tick_count"], 13)
        protection = data["chunk_probe_originals"]
        self.assertTrue(protection["unchanged_verified"])
        self.assertEqual(protection["errors"], [])
        for name in ("A", "B"):
            self.assertEqual(authority_view(protection["before"][name]), authority_view(protection["after"][name]))
            self.assertNotEqual(protection["before"][name]["entity"]["position"],
                                protection["after"][name]["entity"]["position"])

    def test_original_uuid_collision_never_summons_or_changes_tickets(self):
        rcon, data = ProbeRcon([]), self.data()
        with patch.object(fixture, "PROBE_CITIZEN", CITIZEN), self.assertRaisesRegex(ValueError, "collides"):
            fixture.run_chunk_probe(rcon, data, lambda _: None)
        self.assertFalse(any(c.startswith(("summon ", "forceload ", "fill ")) for c in rcon.commands))
        self.assertTrue(data["chunk_probe_originals"]["unchanged_verified"])
        self.assert_no_fallback(rcon)

    def test_preexisting_loaded_or_unavailable_uuid_is_rejected(self):
        for before in (probe_snapshot(), missing_probe("NOT_A_MARKED_VILLAGER"),
                       missing_probe("SNAPSHOT_UNAVAILABLE")):
            with self.subTest(status=before["status"]):
                rcon, data = ProbeRcon([before]), self.data()
                with self.assertRaisesRegex(ValueError, "already loaded|absence is unavailable"):
                    fixture.run_chunk_probe(rcon, data, lambda _: None)
                self.assertFalse(any(c.startswith(("summon ", "forceload ", "fill ")) for c in rcon.commands))
                self.assertTrue(data["chunk_probe_originals"]["unchanged_verified"])
                self.assert_no_fallback(rcon)

    def test_uuid_loaded_by_setup_is_rejected_before_summon(self):
        rcon, data = ProbeRcon([missing_probe(), probe_snapshot()]), self.data()
        with self.assertRaisesRegex(ValueError, "became loaded"):
            fixture.run_chunk_probe(rcon, data, lambda _: None)
        self.assertFalse(any(c.startswith("summon ") for c in rcon.commands))
        self.assertTrue(data["chunk_probe_originals"]["unchanged_verified"])
        self.assert_no_fallback(rcon)

    def test_old_worker_foreign_world_and_unmarked_readiness_fail_closed(self):
        wrong_worker = completed()
        wrong_worker["citizen"] = OTHER
        wrong_world = probe_snapshot()
        wrong_world["world"] = OTHER
        for response in (wrong_worker, wrong_world, missing_probe("NOT_A_MARKED_VILLAGER")):
            with self.subTest(response=response["status"], citizen=response["citizen"], world=response["world"]):
                rcon, data = ProbeRcon([missing_probe(), missing_probe(), response]), self.data()
                with self.assertRaises(ValueError):
                    fixture.run_chunk_probe(rcon, data, lambda _: None)
                self.assertEqual(data["probe_identity"]["readiness"]["polls"], 1)
                self.assertFalse(data["probe_identity"]["readiness"]["ready"])
                self.assertTrue(data["chunk_probe_originals"]["unchanged_verified"])
                self.assert_no_fallback(rcon)

    def test_native_uuid_binding_cannot_return_old_worker(self):
        rcon, data = ProbeRcon([missing_probe(), missing_probe(), probe_snapshot()], native_identity=OTHER), self.data()
        with self.assertRaisesRegex(ValueError, "Native probe UUID witness"):
            fixture.run_chunk_probe(rcon, data, lambda _: None)
        self.assertEqual(native_uuid(data["probe_identity"]["native_uuid_response"]), OTHER)
        self.assertFalse(data["probe_identity"]["readiness"]["ready"])
        self.assertTrue(data["chunk_probe_originals"]["unchanged_verified"])
        self.assert_no_fallback(rcon)

    def test_wrong_position_chunk_marker_noai_or_existing_haul_prevents_ticket_removal(self):
        for corruption in ("position", "chunk", "marker", "no_ai", "haul"):
            response = probe_snapshot()
            if corruption == "position":
                response["entity"]["position"][0] += 1
            elif corruption == "chunk":
                response["entity"]["chunk"][0] += 1
            elif corruption == "marker":
                response["entity"].update(sable_marker=False, citizen_marker=True)
            elif corruption == "no_ai":
                response["entity"]["no_ai"] = False
            else:
                response["haul"] = completed()["haul"]
                response["claim"]["owned_by_citizen"] = False
            with self.subTest(corruption=corruption):
                rcon, data = ProbeRcon([missing_probe(), missing_probe(), response]), self.data()
                with self.assertRaises(ValueError):
                    fixture.run_chunk_probe(rcon, data, lambda _: None)
                self.assertEqual(data["probe_identity"]["readiness"]["polls"], 1)
                self.assertTrue(data["chunk_probe_originals"]["unchanged_verified"])
                self.assert_no_fallback(rcon)

    def test_readiness_timeout_obeys_original_budget_and_finally_checks_originals(self):
        rcon = ProbeRcon([missing_probe()] * (fixture.PROBE_MAX_POLLS + 2))
        data, sleeps = self.data(), []
        with self.assertRaisesRegex(AssertionError, "chunk-probe-readiness"):
            fixture.run_chunk_probe(rcon, data, sleeps.append)
        self.assertEqual(data["probe_identity"]["readiness"]["polls"], 60)
        self.assertEqual(sleeps, [0.25] * 60)
        self.assertEqual(rcon.probe_replies, [])
        self.assertTrue(data["chunk_probe_originals"]["unchanged_verified"])
        self.assert_no_fallback(rcon)

    def test_original_noai_and_authority_changes_fail_the_probe(self):
        for change in (lambda s: s["entity"].update(no_ai=True),
                       lambda s: s["haul"].update(job=WORLD)):
            rcon, data = ProbeRcon(probe_sequence(), after_changes={OTHER: change}), self.data()
            with self.assertRaisesRegex(ValueError, "original-state verification failed"):
                fixture.run_chunk_probe(rcon, data, lambda _: None)
            self.assertFalse(data["chunk_probe_originals"]["unchanged_verified"])
            self.assertEqual(set(data["chunk_probe_originals"]["after"]), {"A", "B"})
            self.assertIn("Original citizen NoAI or stable authority changed", data["chunk_probe_originals"]["errors"][0])
            self.assert_no_fallback(rcon, removed=True)

    def test_primary_timeout_survives_changed_or_unavailable_original_after_read(self):
        for change in (lambda s: s["entity"].update(no_ai=True), RuntimeError("protected read failed")):
            rcon = ProbeRcon([missing_probe()] * (fixture.PROBE_MAX_POLLS + 2), after_changes={OTHER: change})
            data = self.data()
            with self.assertRaisesRegex(AssertionError, "chunk-probe-readiness"):
                fixture.run_chunk_probe(rcon, data, lambda _: None)
            self.assertFalse(data["chunk_probe_originals"]["unchanged_verified"])
            self.assertEqual(len(data["chunk_probe_originals"]["errors"]), 1)
            self.assertIn("A", data["chunk_probe_originals"]["after"])
            self.assert_no_fallback(rcon)

    def test_plan_declares_identity_readiness_and_protection(self):
        plan = fixture.plan(Path(fixture.__file__).resolve().parents[1])["chunk_probe"]
        self.assertEqual(plan["probe_citizen"], str(UUID(fixture.PROBE_CITIZEN)))
        self.assertEqual(plan["identity_policy"], "PREDECLARED_UUID_NATIVE_SUMMON_NO_SELECTOR")
        self.assertEqual(plan["probe_chunk"], (256, 255))
        self.assertEqual(plan["readiness"]["max_polls"], 60)
        self.assertEqual(plan["readiness"]["poll_seconds"], 0.25)
        self.assertTrue(plan["readiness"]["native_uuid_binding"])
        self.assertEqual(plan["initial_nbt"], {"sable_marker": True, "persistence_required": True, "no_ai": True})
        self.assertEqual(plan["protect_originals"], "NOAI_AND_STABLE_AUTHORITY_BEFORE_AND_FINALLY_AFTER")


class DiagnosticEvidenceTests(unittest.TestCase):
    def test_complete_bounded_roundtrip(self):
        value = observed()
        response = PREFIX + json.dumps(value, separators=(",", ":"))
        self.assertLessEqual(len(response.encode()), MAX_RESPONSE_BYTES)
        self.assertEqual(parse_snapshot(response, CITIZEN, WORLD, "minecraft:overworld"), value)
        self.assertEqual(require_blocked_cargo(value, CITIZEN, SOURCE, DESTINATION), JOB)

    def test_exact_identity_and_dimension_binding(self):
        for kwargs in ({"expected_citizen": OTHER}, {"expected_world": OTHER},
                       {"expected_dimension": "minecraft:the_nether"}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                validate_snapshot(observed(), **kwargs)

    def test_missing_required_downstream_fields_rejected(self):
        for path in (("haul", "job"), ("haul", "source"), ("haul", "phase"),
                     ("entity", "tick_count"), ("navigation", "node_count"),
                     ("claim", "source_owner"), ("motor", "intended_target")):
            value = observed()
            del value[path[0]][path[1]]
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate_snapshot(value)

    def test_giant_numbers_and_unmarked_observed_entity_rejected(self):
        for corruption in ("vector", "distance", "marker"):
            value = observed()
            if corruption == "vector":
                value["entity"]["position"][0] = 10 ** 400
            elif corruption == "distance":
                value["motor"]["distance_sq"] = 10 ** 400
            else:
                value["entity"]["sable_marker"] = False
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                validate_snapshot(value)

    def test_missing_or_false_readonly_check_rejected(self):
        for key in READ_ONLY_CHECKS:
            for replacement in (None, False):
                value = observed()
                if replacement is None:
                    del value["read_only_checks"][key]
                else:
                    value["read_only_checks"][key] = replacement
                with self.subTest(key=key, replacement=replacement), self.assertRaises(ValueError):
                    validate_snapshot(value)

    def test_observation_side_effect_is_explicit_unusable_status(self):
        value = observed()
        value.update(status="OBSERVATION_SIDE_EFFECT_DETECTED", strictly_read_only=False)
        value["read_only_checks"]["persistent_nbt_unchanged"] = False
        self.assertEqual(validate_snapshot(value)["status"], "OBSERVATION_SIDE_EFFECT_DETECTED")
        with self.assertRaises(ValueError):
            require_blocked_cargo(value, CITIZEN, SOURCE, DESTINATION)

    def test_authority_flags_fail_closed(self):
        for name, replacement in (("atomic", False), ("strictly_read_only", False),
                                  ("policy_control", True), ("reward_authorized", True)):
            value = observed()
            value[name] = replacement
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_snapshot(value)

    def test_scope_and_serialization_baseline_are_required(self):
        for name in ("observation_scope", "invariant_baseline"):
            for replacement in (None, "WHOLE_WORLD_PURITY"):
                value = observed()
                if replacement is None:
                    del value[name]
                else:
                    value[name] = replacement
                with self.subTest(name=name, replacement=replacement), self.assertRaises(ValueError):
                    validate_snapshot(value)

    def test_duplicate_fields_nonfinite_and_size_rejected(self):
        valid = PREFIX + json.dumps(observed(), separators=(",", ":"))
        with self.assertRaises(ValueError):
            parse_snapshot(valid.replace('"tick":100', '"tick":100,"tick":101'))
        with self.assertRaises(ValueError):
            parse_snapshot(valid.replace('"distance_sq":9.25', '"distance_sq":NaN'))
        with self.assertRaises(ValueError):
            parse_snapshot(valid + " " * MAX_RESPONSE_BYTES)

    def test_command_builder_rejects_non_uuid_or_injected_input(self):
        self.assertEqual(command_for(CITIZEN), "hearthbound-haul-diagnostics " + CITIZEN)
        for candidate in ("@e", "invalid", CITIZEN + " run kill @e", CITIZEN.upper()):
            if candidate == CITIZEN:
                continue
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                command_for(candidate)

    def test_foreign_claim_is_observed_but_not_accepted_as_owned(self):
        value = observed()
        value["claim"].update(source_owner=OTHER, owned_by_citizen=False)
        self.assertEqual(validate_snapshot(value)["claim"]["source_owner"], OTHER)
        with self.assertRaises(ValueError):
            require_blocked_cargo(value, CITIZEN, SOURCE, DESTINATION)
        value["claim"]["owned_by_citizen"] = True
        with self.assertRaises(ValueError):
            validate_snapshot(value)

    def test_malformed_and_absent_cargo_are_not_zero_item_witnesses(self):
        for missing in (True, False):
            value = observed()
            if missing:
                value["haul"]["types"]["cargo"] = 0
                value["haul"]["cargo"].update(present=False, type=0, item=None, count=None, empty=None)
            else:
                value["haul"]["cargo"].update(count=None, empty=None)
            self.assertIsNotNone(validate_snapshot(value))
            with self.assertRaises(ValueError):
                require_blocked_cargo(value, CITIZEN, SOURCE, DESTINATION)

    def test_negative_retained_cargo_remains_anomaly(self):
        value = observed()
        value["haul"]["cargo"].update(count=-1, empty=True)
        self.assertEqual(validate_snapshot(value)["haul"]["cargo"]["count"], -1)
        with self.assertRaises(ValueError):
            require_blocked_cargo(value, CITIZEN, SOURCE, DESTINATION)

    def test_unknown_claim_store_is_not_a_released_claim(self):
        value = observed()
        value["claim"].update(store_present=False, source_owner=None, owned_by_citizen=None, total_claims=None)
        self.assertIsNone(validate_snapshot(value)["claim"]["owned_by_citizen"])
        with self.assertRaises(ValueError):
            require_blocked_cargo(value, CITIZEN, SOURCE, DESTINATION)

    def test_unloaded_and_partial_inventory_witnesses_are_not_complete(self):
        for status in ("CHUNK_UNLOADED", "PARTIAL_SLOT_LIMIT", "LOOT_TABLE_NOT_REALIZED"):
            value = observed()
            value["inventories"]["source"].update(status=status, complete=False, wheat=None, total_items=None)
            self.assertIsNotNone(validate_snapshot(value))
            with self.assertRaises(ValueError):
                require_blocked_cargo(value, CITIZEN, SOURCE, DESTINATION)

    def test_motor_geometry_and_distance_must_match_observed_position(self):
        for key, replacement in (("distance_sq", 25.0), ("within_reach", True),
                                  ("navigation_request_target", [7.5, 100.5, 1.5]),
                                  ("intended_target", SOURCE), ("reach_sq", 16.0)):
            value = observed()
            value["motor"][key] = replacement
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_snapshot(value)

    def test_path_null_is_an_observation_not_a_motor_failure_cause(self):
        value = observed()
        value["navigation"].update(path_present=False, next_node_index=None, node_count=None,
                                   path_can_reach=None, path_target=None, next_node=None, end_node=None)
        self.assertEqual(require_blocked_cargo(value, CITIZEN, SOURCE, DESTINATION), JOB)

    def test_natural_ticks_do_not_change_stable_job_authority(self):
        first, second = observed(), observed()
        second["tick"] += 20
        second["entity"]["tick_count"] += 20
        second["navigation"]["stuck"] = True
        self.assertEqual(authority_view(first), authority_view(second))
        second["haul"]["job"] = OTHER
        self.assertNotEqual(authority_view(first), authority_view(second))

    def test_completed_job_requires_same_job_and_actual_inventory(self):
        require_completed(completed(), CITIZEN, JOB, SOURCE, DESTINATION)
        with self.assertRaises(ValueError):
            require_completed(completed(), CITIZEN, OTHER, SOURCE, DESTINATION)
        value = completed()
        value["inventories"]["destination"] = inventory(0)
        with self.assertRaises(ValueError):
            require_completed(value, CITIZEN, JOB, SOURCE, DESTINATION)

    def test_completed_job_cannot_retain_cargo_or_future_receipt(self):
        for corruption in ("cargo", "future", "claim"):
            value = completed()
            if corruption == "cargo":
                value["haul"]["types"]["cargo"] = 10
                value["haul"]["cargo"] = observed()["haul"]["cargo"]
            elif corruption == "future":
                value["haul"]["delivered_tick"] = value["tick"] + 1
            else:
                value["claim"].update(source_owner=CITIZEN, owned_by_citizen=True, total_claims=1)
            with self.subTest(corruption=corruption), self.assertRaises(ValueError):
                require_completed(value, CITIZEN, JOB, SOURCE, DESTINATION)

    def test_negative_identity_statuses_do_not_pick_a_nearest_worker(self):
        common = {key: val for key, val in observed().items()
                  if key not in ("entity", "haul", "claim", "motor", "navigation", "inventories", "read_only_checks")}
        for status, loaded in (("NOT_LOADED_IN_DIMENSION", False), ("NOT_A_MARKED_VILLAGER", True),
                                ("OVERSIZED_UNAVAILABLE", True), ("SNAPSHOT_UNAVAILABLE", True)):
            value = dict(common, status=status, loaded=loaded)
            self.assertEqual(validate_snapshot(value, CITIZEN)["status"], status)
        invalid = dict(common, status="INVALID_UUID", citizen=None, loaded=False)
        self.assertEqual(validate_snapshot(invalid)["status"], "INVALID_UUID")
        with self.assertRaises(ValueError):
            validate_snapshot(invalid, CITIZEN)

    def test_unavailable_world_and_dimension_are_explicit(self):
        value = observed()
        value.update(world_state="UNAVAILABLE", world=None, dimension_available=False, dimension=None)
        self.assertIsNone(validate_snapshot(value)["world"])
        with self.assertRaises(ValueError):
            validate_snapshot(value, expected_world=WORLD)
        with self.assertRaises(ValueError):
            validate_snapshot(value, expected_dimension="minecraft:overworld")

    def test_native_uuid_requires_one_actual_uuid_array(self):
        raw = "Probe has the following entity data: [I; " + ", ".join(map(str, struct.unpack(">iiii", UUID(CITIZEN).bytes))) + "]"
        self.assertEqual(native_uuid(raw), CITIZEN)
        for value in ("No entity was found", raw + raw, "Probe UUID is " + CITIZEN):
            with self.subTest(value=value), self.assertRaises(ValueError):
                native_uuid(value)


if __name__ == "__main__":
    unittest.main()
