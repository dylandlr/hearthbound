#!/usr/bin/env python3
"""Regression contracts for restart probes with two moving named citizens."""
import unittest

from outcome_restart_identity import checkpoint_identity, executor_command, wait_for_executor


JOB = "28777261-a114-4e0e-b249-4c5fe8506bfd"
CITIZEN = "c422f64c-b3b1-4000-9e65-0b3b9a6dc2bc"
WORLD = "ac7d2d25-b818-47dd-b32b-1a5d4002ac11"
FOREIGN = "00000000-0000-4000-8000-000000000001"


def checkpoint():
    event = f"hearthbound:mill:v1:{WORLD}:minecraft:overworld:{JOB}"
    physical = f"hearthbound:create-process:v1:{WORLD}:minecraft:overworld:1924145352805:{JOB}:72:202"
    return {"schema": "hearthbound.outcome-restart-checkpoint.v1", "job": JOB,
            "receipt": f"MILL_OUTCOME_PROPOSAL status=PROPOSED job={JOB} citizen={CITIZEN} world={WORLD} physical_evidence_id={physical}\n",
            "journal": f"CAUSAL_EVIDENCE_JOURNAL state=ADMITTED revalidated=true event={event} world={WORLD} job={JOB} citizen={CITIZEN} physical_evidence={physical} record_count=1\n",
            "learning": f"MILL_LEARNING_SHADOW status=REPLAYED event={event} citizen={CITIZEN} physical_evidence_id={physical}\n"}


class Clock:
    def __init__(self):
        self.now = 0.0

    def read(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Readiness:
    def __init__(self, replies, clock=None, response_delay=0):
        self.replies, self.clock, self.response_delay = list(replies), clock, response_delay
        self.commands = []

    def run(self, command):
        self.commands.append(command)
        if self.clock is not None:
            self.clock.now += self.response_delay
        return self.replies.pop(0) if self.replies else "Test failed\n"


class OutcomeRestartIdentityTests(unittest.TestCase):
    def test_three_checkpoint_witnesses_resolve_original_executor(self):
        original = checkpoint_identity(checkpoint())
        self.assertEqual((original.job, original.citizen, original.world), (JOB, CITIZEN, WORLD))

    def test_changed_job_owner_world_or_physical_witness_is_rejected(self):
        changes = (("receipt", f"job={JOB}", f"job={FOREIGN}"),
                   ("journal", f"citizen={CITIZEN}", f"citizen={FOREIGN}"),
                   ("journal", f"world={WORLD}", f"world={FOREIGN}"),
                   ("learning", f"citizen={CITIZEN}", f"citizen={FOREIGN}"),
                   ("learning", ":72:202", ":72:203"))
        for name, old, new in changes:
            value = checkpoint(); value[name] = value[name].replace(old, new)
            with self.subTest(name=name, old=old), self.assertRaises(ValueError):
                checkpoint_identity(value)

    def test_ambiguous_missing_and_noncanonical_owner_are_rejected(self):
        duplicate = checkpoint(); duplicate["receipt"] += f" citizen={FOREIGN}"
        missing = checkpoint(); missing["learning"] = missing["learning"].replace(f"citizen={CITIZEN} ", "")
        noncanonical = checkpoint(); noncanonical["receipt"] = noncanonical["receipt"].replace(CITIZEN, CITIZEN.upper())
        for value in (duplicate, missing, noncanonical):
            with self.subTest(value=value), self.assertRaises(ValueError):
                checkpoint_identity(value)

    def test_actor_scoped_commands_follow_original_uuid_not_machine_or_shared_name(self):
        for operation in (f"sable mill-outcome-probe {JOB}", f"sable mill-outcome-journal {JOB}",
                          f"sable mill-learning-probe {JOB}", f"sable mill-release 7 101 1 {JOB}"):
            self.assertEqual(executor_command(CITIZEN, operation), f"execute as {CITIZEN} at @s run {operation}")
        with self.assertRaises(ValueError):
            executor_command(CITIZEN, f"sable mill-outcome-journal {JOB}\nkill @e")

    def test_readiness_waits_only_for_original_citizen_without_mutations(self):
        clock = Clock(); rcon = Readiness(["Test failed\n", "Test failed\n", "Test passed, count: 1\n"])
        wait_for_executor(rcon, CITIZEN, timeout=2, clock=clock.read, sleep=clock.sleep)
        self.assertEqual(rcon.commands, [f"execute if entity {CITIZEN}"] * 3)
        self.assertEqual(clock.now, 0.5)

    def test_two_loaded_named_sables_do_not_substitute_for_original_uuid(self):
        clock = Clock(); rcon = Readiness(["Test passed, count: 2\n"] * 8)
        with self.assertRaisesRegex(AssertionError, "Original outcome executor"):
            wait_for_executor(rcon, CITIZEN, timeout=1, clock=clock.read, sleep=clock.sleep)
        self.assertEqual(clock.now, 1)
        self.assertEqual(rcon.commands, [f"execute if entity {CITIZEN}"] * 4)

    def test_late_success_is_not_accepted_past_readiness_deadline(self):
        clock = Clock(); rcon = Readiness(["Test passed, count: 1\n"], clock, response_delay=2)
        with self.assertRaisesRegex(AssertionError, "readiness window"):
            wait_for_executor(rcon, CITIZEN, timeout=1, clock=clock.read, sleep=clock.sleep)


if __name__ == "__main__":
    unittest.main()
