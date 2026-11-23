"""Regression contracts for original-actor crash verification, without Forge."""
import math
import unittest

from rcon_verify_pickup_crash_boundary import (
    HAUL_PATH, original_executor, strict_uuid,
    verify_unsaved_haul_absent, wait_for_original_executor,
)

EXECUTOR = "eff8f2cb-be90-48c6-a5ec-8345cbc49515"
OTHER = "5615c58c-7a28-4d5a-b5be-2c6b6ed5496b"


class Clock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def read(self):
        return self.now

    def sleep(self, duration):
        self.sleeps.append(duration)
        self.now += duration


class RconStub:
    def __init__(self, responses):
        self.responses = list(responses)
        self.commands = []

    def run(self, command):
        self.commands.append(command)
        if not self.responses:
            raise AssertionError("Unexpected extra RCON query: " + command)
        response = self.responses[0]
        if len(self.responses) > 1:
            self.responses.pop(0)
        return response


class ExecutorIdentityTests(unittest.TestCase):
    def checkpoint(self, executor=EXECUTOR):
        return {"dispatch": "REPORT_HAUL_DISPATCH status=ASSIGNED executor="
                + executor + " recipient=" + executor + " task_assigned=true"}

    def receipt(self, executor=EXECUTOR):
        return "PICKUP_JOURNAL_JOB status=READ_ONLY executor=" + executor

    def test_original_dispatch_and_durable_job_must_agree(self):
        self.assertEqual(original_executor(self.checkpoint(), self.receipt()), EXECUTOR)
        with self.assertRaisesRegex(AssertionError, "differs from original"):
            original_executor(self.checkpoint(), self.receipt(OTHER))

    def test_duplicate_dispatch_identity_is_rejected_even_when_equal(self):
        checkpoint = self.checkpoint()
        checkpoint["dispatch"] += " executor=" + EXECUTOR
        with self.assertRaisesRegex(AssertionError, "Expected one executor"):
            original_executor(checkpoint, self.receipt())

    def test_duplicate_durable_identity_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Expected one executor"):
            original_executor(self.checkpoint(), self.receipt() + " executor=" + OTHER)

    def test_missing_original_identity_cannot_be_inferred_from_journal(self):
        for checkpoint in (None, {}, {"dispatch": "status=ASSIGNED recipient=" + EXECUTOR}):
            with self.subTest(checkpoint=checkpoint), self.assertRaises(AssertionError):
                original_executor(checkpoint, self.receipt())

    def test_missing_durable_executor_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Expected one executor"):
            original_executor(self.checkpoint(), "PICKUP_JOURNAL_JOB status=READ_ONLY")

    def test_executor_uuid_has_strict_canonical_syntax(self):
        invalid = (None, "", "Sable", "@e[name=Sable,limit=1]", EXECUTOR.upper(),
                   EXECUTOR.replace("-", ""), "{" + EXECUTOR + "}",
                   "urn:uuid:" + EXECUTOR, EXECUTOR + " ", EXECUTOR + ";stop",
                   "z" + EXECUTOR[1:])
        for identity in invalid:
            with self.subTest(identity=identity), self.assertRaises(AssertionError):
                strict_uuid(identity, "test")
        self.assertEqual(strict_uuid(EXECUTOR, "test"), EXECUTOR)

    def test_selector_payload_in_either_receipt_is_rejected(self):
        with self.assertRaisesRegex(AssertionError, "Invalid.*UUID"):
            original_executor(self.checkpoint("@e[name=Sable]"), self.receipt())
        with self.assertRaisesRegex(AssertionError, "Invalid.*UUID"):
            original_executor(self.checkpoint(), self.receipt("@e[name=Sable]"))


class ExecutorReadinessTests(unittest.TestCase):
    def wait(self, rcon, clock, **kwargs):
        return wait_for_original_executor(rcon, EXECUTOR, timeout=10.0,
                                          poll_interval=0.25,
                                          clock=clock.read, sleep=clock.sleep,
                                          **kwargs)

    def test_delayed_original_actor_is_read_only_and_uuid_scoped(self):
        clock = Clock()
        rcon = RconStub(["No entity was found\n", "Test failed\n",
                         "Test passed, count: 1\n"])
        result = self.wait(rcon, clock)
        self.assertEqual(result, {"executor": EXECUTOR, "attempts": 3,
                                  "wait_seconds": 0.5, "timeout_seconds": 10.0})
        self.assertEqual(rcon.commands, ["execute if entity " + EXECUTOR] * 3)
        self.assertEqual(clock.sleeps, [0.25, 0.25])

    def test_already_loaded_actor_needs_no_sleep(self):
        clock = Clock()
        rcon = RconStub(["Test passed, count: 1"])
        self.assertEqual(self.wait(rcon, clock)["wait_seconds"], 0.0)
        self.assertEqual(clock.sleeps, [])

    def test_missing_original_actor_fails_at_bounded_deadline(self):
        clock = Clock()
        rcon = RconStub(["Test failed"])
        with self.assertRaisesRegex(AssertionError, "MISSING_BASELINE_EXECUTOR executor="
                                    + EXECUTOR):
            self.wait(rcon, clock)
        self.assertEqual(clock.now, 10.0)
        self.assertEqual(len(rcon.commands), 40)
        self.assertTrue(all(command == "execute if entity " + EXECUTOR
                            for command in rcon.commands))

    def test_another_citizen_named_sable_cannot_satisfy_readiness(self):
        clock = Clock()

        class AnotherSable:
            commands = []

            def run(self, command):
                self.commands.append(command)
                return ("Test passed, count: 1" if "name=Sable" in command
                        or OTHER in command else "No entity was found")

        rcon = AnotherSable()
        with self.assertRaisesRegex(AssertionError, "MISSING_BASELINE_EXECUTOR"):
            self.wait(rcon, clock)
        self.assertTrue(all(command == "execute if entity " + EXECUTOR
                            for command in rcon.commands))

    def test_actor_visible_only_after_deadline_is_not_promoted(self):
        clock = Clock()

        class SlowProbe:
            def run(self, command):
                clock.now = 10.1
                return "Test passed, count: 1"

        with self.assertRaisesRegex(AssertionError, "MISSING_BASELINE_EXECUTOR"):
            self.wait(SlowProbe(), clock)
        self.assertEqual(clock.sleeps, [])

    def test_unexpected_response_or_count_is_not_readiness(self):
        for response in ("Test passed, count: 2", "Test passed", "", "Unknown command",
                         "Test passed, count: 1\nNo entity was found"):
            with self.subTest(response=response):
                clock = Clock()
                with self.assertRaisesRegex(AssertionError, "Unexpected.*readiness"):
                    self.wait(RconStub([response]), clock)
                self.assertEqual(clock.sleeps, [])

    def test_injected_stalled_clock_cannot_query_forever(self):
        rcon = RconStub(["Test failed"])
        with self.assertRaisesRegex(AssertionError, "MISSING_BASELINE_EXECUTOR"):
            wait_for_original_executor(rcon, EXECUTOR, timeout=1, poll_interval=0.25,
                                       clock=lambda: 0, sleep=lambda _: None)
        self.assertEqual(len(rcon.commands), 5)

    def test_invalid_time_budgets_fail_before_query(self):
        for bound in (0, -1, math.inf, math.nan):
            for keyword in ("timeout", "poll_interval"):
                with self.subTest(bound=bound, keyword=keyword):
                    rcon = RconStub(["Test passed, count: 1"])
                    with self.assertRaises(ValueError):
                        wait_for_original_executor(rcon, EXECUTOR, **{keyword: bound})
                    self.assertEqual(rcon.commands, [])


class UnsavedHaulTests(unittest.TestCase):
    def test_original_actor_exists_but_unsaved_haul_does_not(self):
        absent = "Found no elements matching " + HAUL_PATH + "\n"
        rcon = RconStub([absent])
        self.assertEqual(verify_unsaved_haul_absent(rcon, EXECUTOR), absent)
        self.assertEqual(rcon.commands, [f"data get entity {EXECUTOR} {HAUL_PATH}"])

    def test_actor_disappearing_after_readiness_is_still_a_failure(self):
        with self.assertRaisesRegex(AssertionError, "MISSING_BASELINE_EXECUTOR"):
            verify_unsaved_haul_absent(RconStub(["No entity was found"]), EXECUTOR)

    def test_any_restored_haul_is_rejected(self):
        for response in (
            "Sable has the following entity data: {}",
            'Sable has the following entity data: {phase: 0, jobId: [I; 1, 2, 3, 4]}',
            'Sable has the following entity data: {note: "Found no elements matching '
                + HAUL_PATH + '"}',
        ):
            with self.subTest(response=response), self.assertRaisesRegex(
                    AssertionError, "Unsaved assignment"):
                verify_unsaved_haul_absent(RconStub([response]), EXECUTOR)

    def test_missing_other_path_or_malformed_response_is_not_haul_absence(self):
        for response in ("Found no elements matching ForgeData",
                         "Found no elements matching Inventory", "Found no elements",
                         "", "Found no elements matching " + HAUL_PATH + " extra"):
            with self.subTest(response=response), self.assertRaisesRegex(
                    AssertionError, "could not be verified"):
                verify_unsaved_haul_absent(RconStub([response]), EXECUTOR)

    def test_delayed_readiness_still_requires_unsaved_haul_absence(self):
        clock = Clock()
        rcon = RconStub(["Test failed", "Test passed, count: 1",
                         "Sable has the following entity data: {phase: 2}"])
        wait_for_original_executor(rcon, EXECUTOR, clock=clock.read, sleep=clock.sleep)
        with self.assertRaisesRegex(AssertionError, "Unsaved assignment"):
            verify_unsaved_haul_absent(rcon, EXECUTOR)
        self.assertEqual(rcon.commands[-1], f"data get entity {EXECUTOR} {HAUL_PATH}")


if __name__ == "__main__":
    unittest.main()
