#!/usr/bin/env python3
"""Behavioral arrival evidence regressions; no Forge execution is claimed."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from haul_arrival_evidence import (
    ArrivalEvidence, PREFIX, SCHEMA, SOURCE, DESTINATION, distances, native_uuid,
    parse_response, verify_delivery, replay_evidence, TRANSFER_QUERY,
)

WORLD = "10000000-0000-4000-8000-000000000001"
SESSION = "10000000-0000-4000-8000-000000000002"
CITIZEN = "10000000-0000-4000-8000-000000000003"
JOB = "10000000-0000-4000-8000-000000000004"
OTHER = "10000000-0000-4000-8000-000000000005"
BINDING = {"world": WORLD, "session": SESSION, "dimension": "minecraft:overworld",
           "citizen": CITIZEN, "job": JOB, "assigned_tick": 80,
           "source": SOURCE, "destination": DESTINATION}


def inventory(count):
    return {"status": "OBSERVED", "scope": "LOCAL_VANILLA_CONTAINER_NBT",
            "slots": 27, "inspected_slots": 27, "wheat": count,
            "total_items": count, "complete": True}


def sample(tick, position, source, destination):
    # Fixture distances are explicit for the two main cases, independently
    # specified from the verifier's computation.
    if position == [6.0, 100.0, 1.5]:
        motor, smoke = 2.5, 2.25
    elif position == [20.0, 100.0, 1.5]:
        motor, smoke = 156.5, 156.25
    elif position == [7.5, 103.0, 1.5]:
        motor, smoke = 6.25, 9.0
    else:
        raise AssertionError("Declare fixture distance explicitly")
    return {"tick": tick, "position": position, "source": inventory(source),
            "destination": inventory(destination), "motor_distance_sq": motor,
            "smoke_distance_sq": smoke}


def fixture(later_movement=False):
    before = sample(100, [6.0, 100.0, 1.5], 7, 0)
    after = sample(100, [6.0, 100.0, 1.5], 7, 1)
    later = sample(140, [20.0, 100.0, 1.5] if later_movement else [6.0, 100.0, 1.5], 7, 1)
    return {"schema": SCHEMA, "status": "OBSERVED", "world": WORLD, "session": SESSION,
            "dimension": "minecraft:overworld", "citizen": CITIZEN, "tick": 140,
            "observation_scope": "LOCAL_VANILLA_CONTAINER_NBT", "reward_authorized": False,
            "binding": deepcopy(BINDING), "phase": 2, "cargo_present": False,
            "delivered_tick": 100, "current": later,
            "witness": {"status": "OBSERVED", "binding": deepcopy(BINDING),
                        "cargo": {"item": "minecraft:wheat", "count": 1},
                        "before": before, "after": after}}


def encode(value):
    return PREFIX + json.dumps(value, separators=(",", ":"))


class ArrivalContractTest(unittest.TestCase):
    def reject(self, value):
        with self.assertRaises((ValueError, TypeError)):
            verify_delivery(value, BINDING)

    def test_valid_stationary_delivery_preserves_inventory_and_both_radii(self):
        result = verify_delivery(parse_response(encode(fixture())), BINDING)
        self.assertTrue(result["arrival_verified_at_insertion"])
        self.assertEqual(result["before_motor_distance_sq"], 2.5)
        self.assertEqual(result["after_smoke_distance_sq"], 2.25)
        self.assertTrue(result["later_snapshot_within_smoke_radius"])
        self.assertFalse(result["reward_authorized"])

    def test_valid_delivery_then_movement_retains_distinct_observations(self):
        result = verify_delivery(fixture(True), BINDING)
        self.assertTrue(result["arrival_verified_at_insertion"])
        self.assertTrue(result["later_position_differs"])
        self.assertFalse(result["later_snapshot_within_smoke_radius"])
        self.assertEqual(result["insertion_tick"], 100)
        self.assertEqual(result["query_tick"], 140)

    def test_later_arrival_cannot_rescue_remote_insertion(self):
        for stage in ("before", "after"):
            with self.subTest(stage=stage):
                value = fixture()
                value["witness"][stage] = sample(100, [20.0, 100.0, 1.5], 7,
                                                  0 if stage == "before" else 1)
                value["witness"]["within_radius"] = True
                self.reject(value)

    def test_geometry_mismatch_cannot_be_laundered_by_motor_gate(self):
        value = fixture()
        value["witness"]["before"] = sample(100, [7.5, 103.0, 1.5], 7, 0)
        self.reject(value)  # motor exactly 2.5, smoke 3.0

    def test_exact_thresholds_not_expanded(self):
        self.assertEqual(distances([7.5, 103.0, 1.5], DESTINATION), (6.25, 9.0))
        value = fixture()
        pos = [10.100000001, 100.0, 1.5]
        value["witness"]["before"]["position"] = pos
        motor, smoke = distances(pos, DESTINATION)
        value["witness"]["before"].update(motor_distance_sq=motor, smoke_distance_sq=smoke)
        self.reject(value)

    def test_no_witness_phase_or_motor_return_is_insufficient(self):
        for witness in (None, {}, {"status": "UNAVAILABLE"}, {"status": "OBSERVED", "motor_returned": True}):
            with self.subTest(witness=witness):
                value = fixture()
                value["witness"] = witness
                self.reject(value)

    def test_foreign_and_stale_identities_fail(self):
        for container in ("binding", "witness_binding", "current_identity"):
            for name in ("world", "session", "citizen", "job"):
                if container == "current_identity" and name == "job":
                    continue
                with self.subTest(container=container, name=name):
                    value = fixture()
                    target = value if container == "current_identity" else (
                        value["binding"] if container == "binding" else value["witness"]["binding"])
                    target[name] = OTHER
                    self.reject(value)

    def test_foreign_endpoints_dimension_or_assignment_tick_fail(self):
        for name, altered in (("source", [4, 100, 1]), ("destination", [8, 100, 1]),
                              ("dimension", "minecraft:the_nether"), ("assigned_tick", 79)):
            with self.subTest(name=name):
                value = fixture()
                value["witness"]["binding"][name] = altered
                self.reject(value)

    def test_boolean_aliases_are_not_numbers(self):
        for mutate in (
            lambda v: v["witness"]["binding"]["source"].__setitem__(2, True),
            lambda v: v["witness"]["cargo"].__setitem__("count", True),
            lambda v: v["witness"]["after"]["destination"].__setitem__("wheat", True),
            lambda v: v.__setitem__("phase", True),
        ):
            value = fixture()
            mutate(value)
            self.reject(value)

    def test_wrong_or_missing_native_inventory_fails(self):
        for stage in ("before", "after", "current"):
            for endpoint in ("source", "destination"):
                for name, altered in (("status", "CHUNK_UNLOADED"), ("complete", False),
                                      ("slots", 54), ("inspected_slots", 1), ("wheat", 100),
                                      ("total_items", 100)):
                    with self.subTest(stage=stage, endpoint=endpoint, name=name):
                        value = fixture()
                        target = value["current"] if stage == "current" else value["witness"][stage]
                        target[endpoint][name] = altered
                        self.reject(value)

    def test_existing_destination_item_is_not_proof_of_this_delivery(self):
        value = fixture()
        value["witness"]["before"]["destination"] = inventory(1)
        self.reject(value)

    def test_same_tick_completion_and_chronology_are_required(self):
        for stage, tick in (("before", 101), ("after", 99), ("after", 141), ("before", 79)):
            value = fixture()
            value["witness"][stage]["tick"] = tick
            self.reject(value)
        for field, altered in (("delivered_tick", 99), ("phase", 4), ("cargo_present", True), ("tick", 139)):
            value = fixture()
            value[field] = altered
            self.reject(value)

    def test_nonfinite_coordinates_and_false_native_distances_fail(self):
        for altered in (float("nan"), float("inf"), True, "6.0"):
            value = fixture()
            value["witness"]["before"]["position"][0] = altered
            self.reject(value)
        value = fixture()
        value["witness"]["before"]["motor_distance_sq"] = 0
        self.reject(value)

    def test_duplicate_trailing_unavailable_and_oversized_json_fail(self):
        raw = encode(fixture())
        for text in (raw.replace('"status":"OBSERVED"', '"status":"OBSERVED","status":"OBSERVED"', 1),
                     raw + " extra", raw.replace('"tick":140', '"tick":NaN', 1),
                     PREFIX + '{"schema":"' + SCHEMA + '","status":"UNAVAILABLE"}',
                     raw + " " * 4000):
            with self.subTest(text=text[:50]), self.assertRaises(ValueError):
                parse_response(text)

    def test_native_uuid_has_exact_signed_int_components(self):
        self.assertEqual(native_uuid("Sable has the following entity data: [I;268435456,16384,-2147483648,3]"), CITIZEN)
        for text in ("no entity", "[I;1,2,3,4] [I;1,2,3,4]", "[I;4294967296,0,0,1]"):
            with self.assertRaises(ValueError):
                native_uuid(text)


class SimulatedRconArrivalTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "evidence.json"
        self.record = ArrivalEvidence(self.path, metadata={"native_runtime_executed": False,
                                                          "checked_out_sha": "a" * 40})
        self.queries = []

    def transport(self, final=None, later="Test failed", bad_id=False):
        final = fixture(True) if final is None else final
        def command(request_id, query):
            self.queries.append(query)
            if request_id == 94:
                return request_id, "Sable has the following entity data: [I;268435456,16384,-2147483648,3]"
            if request_id == 95:
                return request_id, encode(fixture())
            if request_id == 301:
                return (999 if bad_id else request_id), later
            if query.startswith("hearthbound-haul-arrival "):
                return request_id, encode(final)
            return request_id, "native failure diagnostic"
        return command

    def ready(self, command):
        self.record.bind(command, "AUDIT job=" + JOB + " phase=0")
        self.record.record_poll(100, 100, TRANSFER_QUERY, "Test failed")
        self.record.record_poll(101, 101, TRANSFER_QUERY, "Test passed, count: 1")
        self.record.record_transfer(2, True)
        self.record.record_source_check(300, "Test passed, count: 1")

    def test_event_time_arrival_passes_with_later_query_failure_retained(self):
        command = self.transport()
        self.ready(command)
        result = self.record.check_delivery(command)
        self.assertFalse(result["later_query_within_smoke_radius"])
        evidence = json.loads(self.path.read_text())
        self.assertEqual(evidence["status"], "PASSED")
        self.assertTrue(evidence["validation"]["arrival_verified_at_insertion"])
        self.assertIn("Test failed", [row["response"] for row in evidence["responses"]])
        self.assertTrue(any("as " + CITIZEN in q and "distance=..2.6" in q for q in self.queries))
        self.assertFalse(any(token in q for q in self.queries for token in (" tp ", "NoAI", "setblock", "data modify")))

    def test_remote_insertion_fails_even_if_later_query_passes_and_preserves_diagnostics(self):
        value = fixture()
        value["witness"]["before"] = sample(100, [20.0, 100.0, 1.5], 7, 0)
        command = self.transport(value, later="Test passed, count: 1")
        self.ready(command)
        with self.assertRaises(ValueError):
            self.record.check_delivery(command)
        evidence = json.loads(self.path.read_text())
        self.assertEqual(evidence["status"], "FAILED")
        self.assertEqual(len(evidence["failure_diagnostics"]), 5)
        self.assertTrue(any(" Pos" in x["command"] for x in evidence["failure_diagnostics"]))
        self.assertTrue(any("haul-audit" in x["command"] for x in evidence["failure_diagnostics"]))
        self.assertTrue(any("block 3 100 1 Items" in x["command"] for x in evidence["failure_diagnostics"]))
        self.assertTrue(any("block 7 100 1 Items" in x["command"] for x in evidence["failure_diagnostics"]))

    def test_wrong_response_id_is_not_success(self):
        command = self.transport(bad_id=True)
        self.ready(command)
        with self.assertRaisesRegex(ValueError, "response ID mismatch"):
            self.record.check_delivery(command)
        self.assertEqual(json.loads(self.path.read_text())["status"], "FAILED")

    def test_legacy_physical_checks_cannot_be_skipped(self):
        command = self.transport()
        self.record.bind(command, "AUDIT job=" + JOB + " phase=0")
        with self.assertRaisesRegex(ValueError, "destination poll did not pass"):
            self.record.check_delivery(command)
        self.record.record_transfer(1, True)
        with self.assertRaisesRegex(ValueError, "source assertion did not pass"):
            self.record.check_delivery(command)

    def test_unavailable_witness_keeps_raw_response_and_failure(self):
        value = fixture()
        value["witness"] = {"status": "UNAVAILABLE", "error_type": "IllegalStateException"}
        command = self.transport(value)
        self.ready(command)
        with self.assertRaises(ValueError):
            self.record.check_delivery(command)
        evidence = json.loads(self.path.read_text())
        self.assertEqual(evidence["status"], "FAILED")
        self.assertTrue(any("UNAVAILABLE" in row.get("response", "") for row in evidence["responses"]))

    def test_offline_replay_recomputes_from_native_raw_responses(self):
        command = self.transport()
        self.ready(command)
        self.record.check_delivery(command)
        value = json.loads(self.path.read_text())
        value["validation"] = {"arrival_verified_at_insertion": False, "made_up_distance": 0}
        result = replay_evidence(value, "a" * 40)
        self.assertTrue(result["arrival_verified_at_insertion"])
        self.assertEqual(result["later_smoke_distance_sq"], 156.25)
        self.assertFalse(result["later_query_within_smoke_radius"])

    def test_offline_replay_rejects_source_identity_poll_and_native_response_tampering(self):
        command = self.transport()
        self.ready(command)
        self.record.check_delivery(command)
        original = json.loads(self.path.read_text())
        for mutate in (
            lambda v: v["provenance"].__setitem__("checked_out_sha", "b" * 40),
            lambda v: v["transfer_responses"].clear(),
            lambda v: v["transfer_responses"][1].__setitem__("response", "Test failed"),
            lambda v: v["source_count_check"].__setitem__("response", "Test failed"),
            lambda v: v["responses"][3].__setitem__("response", encode(dict(fixture(), witness=None))),
            lambda v: v["responses"].append(v["responses"][3]),
        ):
            value = deepcopy(original)
            mutate(value)
            with self.assertRaises(ValueError):
                replay_evidence(value, "a" * 40)

    def test_float_response_ids_fail_in_every_retained_record_kind(self):
        command = self.transport()
        self.ready(command)
        self.record.check_delivery(command)
        original = json.loads(self.path.read_text())
        for kind, indices in (("responses", range(4)), ("transfer_responses", range(2)),
                              ("source_count_check", [None])):
            for index in indices:
                for field in ("request_id", "response_id"):
                    with self.subTest(kind=kind, index=index, field=field):
                        value = deepcopy(original)
                        row = value[kind] if index is None else value[kind][index]
                        row[field] = float(row[field])
                        with self.assertRaises(ValueError):
                            replay_evidence(value)

    def test_query_chronology_cannot_regress_but_fast_delivery_is_allowed(self):
        value = fixture(True)
        value["tick"] = value["current"]["tick"] = 139
        command = self.transport(value)
        self.ready(command)  # initial query tick=140, insertion tick=100
        with self.assertRaisesRegex(ValueError, "predates initial binding query"):
            self.record.check_delivery(command)
        self.assertEqual(json.loads(self.path.read_text())["status"], "FAILED")
        # The event may legitimately precede the first binding observation.
        # The recorded assignment/job still binds it; only query order is fenced.
        self.record = ArrivalEvidence(self.path, metadata={"native_runtime_executed": False})
        command = self.transport(fixture(True))
        self.ready(command)
        result = self.record.check_delivery(command)
        self.assertEqual(result["insertion_tick"], 100)
        self.assertEqual(result["query_tick"], 140)


if __name__ == "__main__":
    unittest.main()
