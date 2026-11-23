import copy
import unittest
from uuid import UUID

from rcon_colony_completion_boundary import (
    DESTINATION, SOURCE, packed_position, parse_trace, saved_uuid,
    validate_pending_motor, validate_persisted, validate_state,
)


def completed_state(completed=2):
    return {
        "board": {"enabled": "false", "queued": 0, "held": 0,
                  "done": completed, "assigned": 0, "distinct_completed_citizens": 1},
        "history": {"records": completed, "physically_completed": completed,
                    "assigned_without_verified_completion": 0, "capacity_denials": 0},
        "reconciliation": {"done": str(completed), "assigned": "0",
                           "assigned_loaded_physically_complete": "0",
                           "assigned_unloaded": "0", "assigned_loaded_incomplete": "0",
                           "strictly_read_only": "true", "reward_authorized": "false"},
        "outstanding_claims": 0,
    }


def uid(number):
    return str(UUID(int=(0xabcdef01 << 96) + number))


def uuid_array(value):
    number = UUID(value).int
    parts = [(number >> shift) & 0xffffffff for shift in (96, 64, 32, 0)]
    return [part if part < 0x80000000 else part - 0x100000000 for part in parts]


def traces_and_save():
    traces, tasks, history = [], [], []
    for task_id in (1, 2):
        trace = {"task": task_id, "citizen": uid(1), "job": uid(10 + task_id),
                 "decision": uid(20 + task_id), "evidence": uid(30 + task_id),
                 "episode": uid(2), "revision": task_id,
                 "observed": task_id * 20, "decided": task_id * 20,
                 "assigned": task_id * 20, "delivered": task_id * 20 + 10}
        traces.append(trace)
        tasks.append({"id": task_id, "owner": uuid_array(trace["citizen"]),
                      "job": uuid_array(trace["job"]), "assignedTick": trace["assigned"],
                      "dimension": "minecraft:overworld", "source": packed_position(SOURCE),
                      "destination": packed_position(DESTINATION),
                      "state": "DONE"})
        record = dict(trace, source=packed_position(SOURCE), destination=packed_position(DESTINATION),
                      status="PHYSICALLY_COMPLETED")
        for key in ("citizen", "job", "decision", "evidence", "episode"):
            record[key] = uuid_array(record[key])
        history.append(record)
    return traces, {"tasks": tasks, "decisionHistory": history, "historyDeniedCapacity": 0,
                    "destination": packed_position(DESTINATION)}


class CompletionBoundaryEvidenceTests(unittest.TestCase):
    def test_completed_state_rejects_disabled_accounting_failure(self):
        validate_state(completed_state(), 2)
        mutations = (
            lambda d: d["board"].update(enabled="true"),
            lambda d: d["board"].update(done=1, assigned=1),
            lambda d: d["board"].update(held=1),
            lambda d: d["board"].update(distinct_completed_citizens=2),
            lambda d: d["history"].update(physically_completed=1),
            lambda d: d["history"].update(records=3),
            lambda d: d["history"].update(capacity_denials=1),
            lambda d: d["reconciliation"].update(assigned_loaded_physically_complete="1"),
            lambda d: d.update(outstanding_claims=1),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                observed = completed_state()
                mutation(observed)
                with self.assertRaises(AssertionError):
                    validate_state(observed, 2)

    def test_pending_boundary_requires_unfinished_owned_motor(self):
        pending = completed_state(1)
        pending["board"].update(assigned=1)
        pending["history"].update(records=2, assigned_without_verified_completion=1)
        pending["reconciliation"].update(assigned="1", assigned_loaded_incomplete="1")
        pending["outstanding_claims"] = 1
        validate_state(pending, 1, pending=1)
        premature = copy.deepcopy(pending)
        premature["reconciliation"].update(assigned_loaded_physically_complete="1",
                                           assigned_loaded_incomplete="0")
        with self.assertRaises(AssertionError):
            validate_state(premature, 1, pending=1)

    def test_already_delivered_motor_cannot_establish_disabled_boundary(self):
        for phase in (0, 1):
            validate_pending_motor({"phase": phase})
        for phase in (2, 3, 4, 5, 6):
            with self.subTest(phase=phase), self.assertRaises(AssertionError):
                validate_pending_motor({"phase": phase})

    def test_trace_requires_exact_job_and_chronology(self):
        text = (f"COLONY_TRACES_V0_4 count=1 episode={uid(2)} "
                f"entries=1,{uid(1)},{uid(11)},{uid(21)},{uid(31)},1,20,20,20,30 "
                "learning_authorized=false reward_authorized=false")
        self.assertEqual(parse_trace(text, uid(11))["citizen"], uid(1))
        for invalid, job in ((text, uid(12)), (text.replace(",20,20,20,30", ",20,20,20,19"), uid(11)),
                             (text.replace("count=1", "count=2"), uid(11)),
                             (text.replace("reward_authorized=false", "reward_authorized=true"), uid(11))):
            with self.subTest(invalid=invalid, job=job), self.assertRaises(AssertionError):
                parse_trace(invalid, job)

    def test_saved_identity_validation_rejects_duplicates_and_cross_job_credit(self):
        traces, saved = traces_and_save()
        validate_persisted(saved, traces)
        self.assertEqual(saved_uuid(uuid_array(uid(1))), uid(1))
        mutations = (
            lambda d: d["tasks"][1].update(job=d["tasks"][0]["job"]),
            lambda d: d["tasks"][1].update(owner=uuid_array(uid(3))),
            lambda d: d["tasks"][1].update(state="ASSIGNED"),
            lambda d: d["decisionHistory"][1].update(status="ASSIGNED"),
            lambda d: d["decisionHistory"][1].update(assigned=0),
            lambda d: d["decisionHistory"][1].update(delivered=1000),
            lambda d: d["decisionHistory"][1].update(evidence=uuid_array(uid(999))),
            lambda d: d["decisionHistory"][1].update(source=packed_position("5 101 8")),
            lambda d: d.update(destination=packed_position("15 101 8")),
            lambda d: d["decisionHistory"].append(copy.deepcopy(d["decisionHistory"][0])),
            lambda d: d["tasks"].pop(),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                invalid = copy.deepcopy(saved)
                mutation(invalid)
                with self.assertRaises(AssertionError):
                    validate_persisted(invalid, traces)

    def test_joint_task_and_history_endpoint_rebinding_is_rejected(self):
        traces, saved = traces_and_save()
        for endpoint, replacement in (("source", "5 101 8"), ("destination", "15 101 8")):
            with self.subTest(endpoint=endpoint):
                invalid = copy.deepcopy(saved)
                invalid["tasks"][1][endpoint] = packed_position(replacement)
                invalid["decisionHistory"][1][endpoint] = packed_position(replacement)
                with self.assertRaises(AssertionError):
                    validate_persisted(invalid, traces)


if __name__ == "__main__":
    unittest.main()
