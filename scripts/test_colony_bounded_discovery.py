import copy
import unittest
from uuid import UUID

from rcon_colony_bounded_discovery import (
    DESTINATION, DIMENSION, EMPTY, FAR, MARKER, SCHEMA, SOURCE,
    collect_audit, packed_position, validate_audit, validate_result, xyz,
)


def uid(number):
    return str(UUID(int=(0xabcdef01 << 96) + number))


def uuid_array(value):
    number = UUID(value).int
    parts = [(number >> shift) & 0xffffffff for shift in (96, 64, 32, 0)]
    return [part if part < 0x80000000 else part - 0x100000000 for part in parts]


def observation(sequence, source, state, wheat, task=None):
    observer = [12.5, 101.0, 8.5]
    return {"sequence": sequence, "world": uid(1), "episode": uid(2),
            "dimension": DIMENSION, "citizen": uid(3), "tick": 100 + sequence,
            "source": xyz(source), "observer": observer,
            "destination": xyz(DESTINATION),
            "distance_squared": sum((a + 0.5 - b) ** 2 for a, b in zip(xyz(source), observer)),
            "state": state, "wheat": wheat, "reason": "OBSERVED",
            "origin": "BOUNDED_IDLE_DISCOVERY", "task_id": task,
            "proposal": "CREATED" if task else "NONE"}


def audit():
    return {"schema": SCHEMA, "world": uid(1), "episode": uid(2),
            "dimension": DIMENSION, "citizen": uid(3), "read_only": True,
            "scope": "SESSION_LOCAL_INCREMENTAL_FALLBACK", "retained": True,
            "counter_scope": "RETAINED_CITIZEN_CURSOR_LIFETIME",
            "citizen_evictions": 0, "observation_evictions": 0,
            "retained_citizens": 1, "retained_observations": 2,
            "bounds": {"positions_per_opportunity": 75, "inspections_per_opportunity": 4,
                       "cadence_ticks": 20, "citizens": 256, "observations": 128, "page_size": 2},
            "stats": {"opportunities": 20, "probes": 1500, "inspections": 2, "proposals": 1,
                      "max_cycle_probes": 75, "max_cycle_inspections": 1,
                      "last_tick": 400, "cursor": 1500, "anchor": [12, 101, 8], "cycles": 0},
            "observation_total": 2,
            "observations": [observation(1, EMPTY, "EMPTY", 0),
                             observation(2, SOURCE, "AVAILABLE", 1, 1)]}


def valid_result():
    trace = {"task": 1, "citizen": uid(3), "job": uid(4), "decision": uid(5),
             "evidence": uid(6), "episode": uid(2), "revision": 1,
             "observed": 120, "decided": 120, "assigned": 120, "delivered": 180}
    task = {"id": 1, "owner": uuid_array(uid(3)), "job": uuid_array(uid(4)),
            "assignedTick": 120, "dimension": DIMENSION, "state": "DONE",
            "source": packed_position(SOURCE), "destination": packed_position(DESTINATION)}
    record = dict(trace, source=packed_position(SOURCE), destination=packed_position(DESTINATION),
                  status="PHYSICALLY_COMPLETED")
    for key in ("citizen", "job", "decision", "evidence", "episode"):
        record[key] = uuid_array(record[key])
    final = {
        "board": {"enabled": "false", "queued": 0, "held": 0, "done": 1,
                  "assigned": 0, "distinct_completed_citizens": 1},
        "history": {"records": 1, "physically_completed": 1,
                    "assigned_without_verified_completion": 0, "capacity_denials": 0},
        "reconciliation": {"done": "1", "assigned": "0", "assigned_loaded_physically_complete": "0",
                           "assigned_unloaded": "0", "assigned_loaded_incomplete": "0",
                           "strictly_read_only": "true", "reward_authorized": "false"},
        "outstanding_claims": 0,
    }
    return {"schema": "hearthbound.colony-bounded-discovery.v1", "tested_commit": "a" * 40,
            "world": uid(1), "citizen": uid(3), "discovery": audit(), "trace": trace,
            "motor": {"job": uid(4), "phase": 2}, "final": final,
            "persisted": {"tasks": [task], "decisionHistory": [record], "historyDeniedCapacity": 0,
                          "destination": packed_position(DESTINATION)},
            "inventories_before": {"source": 1, "empty": 0, "destination": 0, "far": 1},
            "inventories_after": {"source": 0, "empty": 0, "destination": 1, "far": 1},
            "far_memory_status": "UNKNOWN", "behavioral_retries": 0,
            "witness_seconds": 40.0,
            "active_interventions_after_enable": 0, "learning_authorized": False,
            "reward_authorized": False}


class DiscoveryEvidenceTests(unittest.TestCase):
    def test_full_outer_observation_to_real_job_chain(self):
        result = valid_result()
        source, empty = validate_result(result)
        self.assertEqual(source["task_id"], 1)
        self.assertEqual(empty["source"], xyz(EMPTY))

    def test_actual_observer_geometry_not_starting_geometry(self):
        for observer in ([3.5, 101.0, 8.5], [30.5, 101.0, 8.5]):
            with self.subTest(observer=observer):
                result = valid_result()
                entry = result["discovery"]["observations"][1]
                entry["observer"] = observer
                entry["distance_squared"] = sum((a + 0.5 - b) ** 2
                                                 for a, b in zip(entry["source"], observer))
                with self.assertRaises(AssertionError):
                    validate_result(result)

    def test_forged_or_nonfinite_distance_is_rejected(self):
        for distance in (0, 256.1, float("nan"), float("inf")):
            with self.subTest(distance=distance):
                result = valid_result()
                result["discovery"]["observations"][1]["distance_squared"] = distance
                with self.assertRaises(AssertionError):
                    validate_result(result)

    def test_incremental_budgets_and_counters_are_checked(self):
        mutations = (
            lambda a: a["stats"].update(max_cycle_probes=76),
            lambda a: a["stats"].update(max_cycle_inspections=5),
            lambda a: a["stats"].update(probes=1501),
            lambda a: a["stats"].update(inspections=81),
            lambda a: a["stats"].update(proposals=3),
            lambda a: a["stats"].update(opportunities=0),
            lambda a: a["bounds"].update(positions_per_opportunity=750),
            lambda a: a["bounds"].update(cadence_ticks=1),
            lambda a: a.update(read_only=False),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                invalid = audit()
                mutate(invalid)
                with self.assertRaises(AssertionError):
                    validate_audit(invalid, uid(3), uid(1))

    def test_each_observation_has_exact_citizen_world_and_episode(self):
        for key, replacement in (("citizen", uid(99)), ("world", uid(99)),
                                 ("episode", uid(99)), ("dimension", "minecraft:the_nether"),
                                 ("origin", "OPERATOR_REPORT")):
            with self.subTest(key=key):
                invalid = audit()
                invalid["observations"][1][key] = replacement
                with self.assertRaises(AssertionError):
                    validate_audit(invalid, uid(3), uid(1))

    def test_all_rows_require_current_geometry_destination_and_retained_evidence(self):
        mutations = (
            lambda a: a.update(citizen_evictions=1),
            lambda a: a.update(observation_evictions=1),
            lambda a: a.update(counter_scope="SESSION_TOTAL"),
            lambda a: a.update(retained_observations=3),
            lambda a: a["observations"][0].update(destination=xyz(FAR)),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                invalid = audit()
                mutate(invalid)
                with self.assertRaises(AssertionError):
                    validate_audit(invalid, uid(3), uid(1))
        for observer in ([1.5, 101.0, 6.5], [12.5, 103.0, 8.5]):
            invalid = audit()
            row = invalid["observations"][0]
            row["observer"] = observer
            row["distance_squared"] = sum((a + 0.5 - b) ** 2
                                           for a, b in zip(row["source"], observer))
            with self.subTest(observer=observer), self.assertRaises(AssertionError):
                validate_audit(invalid, uid(3), uid(1))

    def test_empty_control_requires_actual_zero_observation_without_credit(self):
        mutations = (
            lambda a: a["observations"][0].update(state="UNKNOWN", reason="CHUNK_UNLOADED"),
            lambda a: a["observations"][0].update(wheat=1),
            lambda a: a["observations"][0].update(task_id=2),
            lambda a: a["observations"][0].update(proposal="CREATED"),
            lambda a: a["observations"][0].update(reason="ASSUMED_EMPTY"),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                invalid = audit()
                mutate(invalid)
                with self.assertRaises(AssertionError):
                    validate_audit(invalid, uid(3), uid(1))

    def test_distant_control_cannot_be_observed_remembered_or_transferred(self):
        result = valid_result()
        extra = observation(3, FAR, "AVAILABLE", 1, 2)
        result["discovery"]["observations"].append(extra)
        result["discovery"]["observation_total"] = 3
        result["discovery"]["retained_observations"] = 3
        result["discovery"]["stats"].update(inspections=3, proposals=2)
        with self.assertRaises(AssertionError):
            validate_result(result)
        for key, replacement in (("far_memory_status", "KNOWN"),):
            result = valid_result()
            result[key] = replacement
            with self.assertRaises(AssertionError):
                validate_result(result)
        result = valid_result()
        result["inventories_after"]["far"] = 0
        with self.assertRaises(AssertionError):
            validate_result(result)

    def test_completed_phase_is_insufficient_without_inventory_deltas(self):
        for endpoint, amount in (("source", 1), ("destination", 0), ("empty", 1)):
            with self.subTest(endpoint=endpoint):
                result = valid_result()
                result["inventories_after"][endpoint] = amount
                with self.assertRaises(AssertionError):
                    validate_result(result)

    def test_decision_and_job_must_bind_the_discovered_task(self):
        mutations = (
            lambda d: d["trace"].update(task=2),
            lambda d: d["trace"].update(citizen=uid(99)),
            lambda d: d["trace"].update(episode=uid(99)),
            lambda d: d["trace"].update(observed=101),
            lambda d: d["trace"].update(assigned=142),
            lambda d: d["trace"].update(delivered=119),
            lambda d: d["motor"].update(job=uid(99)),
            lambda d: d["motor"].update(phase=1),
            lambda d: d["discovery"]["observations"][1].update(proposal="EXISTING"),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                result = valid_result()
                mutate(result)
                with self.assertRaises(AssertionError):
                    validate_result(result)

    def test_joint_saved_endpoint_rebinding_or_extra_task_is_rejected(self):
        for key, position in (("source", FAR), ("destination", EMPTY)):
            with self.subTest(key=key):
                result = valid_result()
                result["persisted"]["tasks"][0][key] = packed_position(position)
                result["persisted"]["decisionHistory"][0][key] = packed_position(position)
                with self.assertRaises(AssertionError):
                    validate_result(result)
        result = valid_result()
        result["persisted"]["tasks"].append(copy.deepcopy(result["persisted"]["tasks"][0]))
        with self.assertRaises(AssertionError):
            validate_result(result)

    def test_proposal_without_completed_history_is_rejected(self):
        mutations = (
            lambda d: d["persisted"]["tasks"][0].update(state="ASSIGNED"),
            lambda d: d["persisted"]["decisionHistory"][0].update(status="ASSIGNED"),
            lambda d: d["final"]["board"].update(done=0, assigned=1),
            lambda d: d["final"]["history"].update(physically_completed=0),
            lambda d: d.update(behavioral_retries=1),
            lambda d: d.update(active_interventions_after_enable=1),
        )
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                result = valid_result()
                mutate(result)
                with self.assertRaises(AssertionError):
                    validate_result(result)

    def test_duplicate_or_reordered_observations_are_rejected(self):
        for sequences in ((1, 1), (2, 1)):
            invalid = audit()
            for entry, sequence in zip(invalid["observations"], sequences):
                entry["sequence"] = sequence
            with self.subTest(sequences=sequences), self.assertRaises(AssertionError):
                validate_audit(invalid, uid(3), uid(1))

    def test_late_or_invalid_witness_window_cannot_pass(self):
        for elapsed in (-1, 150.0, 151.0, float("nan"), float("inf")):
            result = valid_result()
            result["witness_seconds"] = elapsed
            with self.subTest(elapsed=elapsed), self.assertRaises(AssertionError):
                validate_result(result)

    def test_pagination_requires_stable_disabled_metadata(self):
        import json
        base = audit()
        first = dict(base, observations=base["observations"][:1], offset=0, next_offset=1)
        second = dict(base, observations=base["observations"][1:], offset=1, next_offset=None)

        class Replies:
            def __init__(self, replies):
                self.replies = iter(replies)
            def require(self, command, marker):
                return marker + json.dumps(next(self.replies))

        self.assertEqual(collect_audit(Replies([first, second]), uid(3)), base)
        changing = copy.deepcopy(second)
        changing["stats"]["opportunities"] += 1
        with self.assertRaises(AssertionError):
            collect_audit(Replies([first, changing]), uid(3))
        looping = dict(second, next_offset=1)
        with self.assertRaises(AssertionError):
            collect_audit(Replies([first, looping]), uid(3))


if __name__ == "__main__":
    unittest.main()
