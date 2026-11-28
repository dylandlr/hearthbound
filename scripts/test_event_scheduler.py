"""Behavioral, persistence, and killed-process contracts; no Forge execution."""
from dataclasses import FrozenInstanceError
import hashlib
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import unittest
import warnings
from unittest.mock import patch

from event_scheduler import Event, Intent, JournalError, MAX_TICK, Schedule, Scheduler


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "events.journal"
        self.events = [Event("a", "crop_failure", 2, 3, .4)]

    def create(self, events=None):
        s = Scheduler.create(self.path, self.events if events is None else events, "world", "run")
        self.addCleanup(s.close)
        return s

    def reopen(self, events=None, world="world", run="run"):
        s = Scheduler.open(self.path, self.events if events is None else events, world, run)
        self.addCleanup(s.close)
        return s

    def settle(self, s, intent):
        late = intent.observed_tick != intent.transition.tick
        return s.acknowledge(intent.transition.transition_id, "MISSED" if late else "APPLIED",
                             f"evidence-{intent.index}", None if late else intent.transition.tick)

    def test_event_validation(self):
        for name in ["", " ", "x:y", "x\ty", "é", "a" * 65]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                Event(name, "crop_failure", 0, 1, .5)
        for onset, duration, severity in [(-1, 1, .5), (True, 1, .5), (0, 0, .5),
                (0, True, .5), (0, 1, True), (0, 1, float("nan")),
                (0, 1, float("inf")), (0, 1, -.1), (0, 1, 1.1),
                (MAX_TICK, 1, .5), (0, MAX_TICK + 1, .5)]:
            with self.subTest(values=(onset, duration, severity)), self.assertRaises(ValueError):
                Event("a", "crop_failure", onset, duration, severity)
        with self.assertRaises(ValueError):
            Event("a", "unknown", 0, 1, .5)
        self.assertEqual(Event("z", "crop_failure", MAX_TICK - 1, 1, 1).onset, MAX_TICK - 1)

    def test_schedule_validation_and_bounded_generator(self):
        with self.assertRaises(ValueError):
            Schedule(self.events * 2)
        with self.assertRaises(ValueError):
            Schedule([object()])
        seen = []
        def many():
            for i in range(5000):
                seen.append(i)
                yield Event(f"e{i}", "crop_failure", 0, 1, 1)
        with self.assertRaises(ValueError):
            Schedule(many())
        self.assertEqual(len(seen), 4097)

    def test_normalized_digest_and_input_order(self):
        a = Event("a", "crop_failure", 0, 1, 0)
        b = Event("b", "mill_failure", 0, 1, 1)
        self.assertEqual(Schedule([a, b]).digest, Schedule([b, a]).digest)
        self.assertEqual(Schedule([a]).digest,
                         Schedule([Event("a", "crop_failure", 0, 1, -0.)]).digest)
        self.assertEqual(Schedule([b]).digest,
                         Schedule([Event("b", "mill_failure", 0, 1, 1.)]).digest)
        self.assertNotEqual(Schedule([a]).digest, Schedule([b]).digest)

    def test_empty_control_and_unchanged_clock(self):
        s = self.create([])
        self.assertIsNone(s.poll(100))
        size = os.fstat(s._fd).st_size
        self.assertIsNone(s.poll(100))
        self.assertEqual(os.fstat(s._fd).st_size, size)
        s.close()
        r = self.reopen([])
        self.assertEqual((r.cursor, r.receipts, r.pending), (100, (), None))

    def test_boundaries_and_no_reissued_intent(self):
        s = self.create()
        self.assertIsNone(s.poll(1))
        intent = s.poll(2)
        self.assertEqual((intent.transition.phase, intent.transition.tick, intent.observed_tick),
                         ("start", 2, 2))
        self.assertTrue(intent.executable)
        self.assertTrue(intent.transition.transition_id.startswith("world:run:"))
        for tick in [2, 3, 5]:
            with self.subTest(tick=tick), self.assertRaises(ValueError):
                s.poll(tick)
        self.settle(s, intent)
        self.assertIsNone(s.poll(4))
        end = s.poll(5)
        self.assertEqual(end.transition.phase, "end")
        self.settle(s, end)
        self.assertIsNone(s.poll(5))
        self.assertEqual(s.next_index, 2)

    def test_compound_overlap_skips_end_before_start(self):
        events = [Event("b", "mill_failure", 5, 3, 1), self.events[0],
                  Event("c", "communication_failure", 3, 3, 1)]
        s = self.create(events)
        actual = []
        while (intent := s.poll(10)) is not None:
            t = intent.transition
            self.assertFalse(intent.executable)
            actual.append((t.tick, t.phase, t.event_id))
            self.settle(s, intent)
        self.assertEqual(actual, [(2, "start", "a"), (3, "start", "c"), (5, "end", "a"),
                                  (5, "start", "b"), (6, "end", "c"), (8, "end", "b")])
        self.assertTrue(all(r.outcome == "MISSED" for r in s.receipts))

    def test_clock_types_bounds_and_backward(self):
        s = self.create([])
        s.poll(3)
        for tick in [2, -1, True, 3., MAX_TICK + 1]:
            with self.subTest(tick=tick), self.assertRaises(ValueError):
                s.poll(tick)
        self.assertEqual(s.cursor, 3)

    def test_pending_requires_reconciliation_after_reopen(self):
        s = self.create()
        intent = s.poll(2)
        s.close()
        r = self.reopen()
        self.assertTrue(r.pending.recovery_required)
        self.assertFalse(r.pending.executable)
        with self.assertRaises(ValueError):
            r.poll(2)
        with self.assertRaises(ValueError):
            r.acknowledge(intent.transition.transition_id, "APPLIED", "witness", 2)
        self.assertTrue(r.reconcile(intent.transition.transition_id, "APPLIED", "witness", 2))
        self.assertIsNone(r.poll(2))
        self.assertEqual(r.next_index, 1)

    def test_reconcile_not_applied_never_retries(self):
        s = self.create()
        intent = s.poll(2)
        with self.assertRaises(ValueError):
            s.reconcile(intent.transition.transition_id, "NOT_APPLIED", "witness")
        s.close()
        r = self.reopen()
        r.reconcile(intent.transition.transition_id, "NOT_APPLIED", "absent-witness")
        self.assertIsNone(r.poll(2))
        self.assertEqual(r.receipts[0].outcome, "NOT_APPLIED")

    def test_duplicate_receipt_idempotency_and_conflicts(self):
        s = self.create()
        intent = s.poll(2)
        self.assertTrue(self.settle(s, intent))
        self.assertFalse(self.settle(s, intent))
        for outcome, evidence, effect in [("FAILED", "evidence-0", None),
                                         ("APPLIED", "different", 2), ("APPLIED", "evidence-0", 3)]:
            with self.subTest(outcome=outcome, evidence=evidence, effect=effect), self.assertRaises(ValueError):
                s.acknowledge(intent.transition.transition_id, outcome, evidence, effect)
        with self.assertRaises(ValueError):
            s.reconcile(intent.transition.transition_id, "APPLIED", "evidence-0", 2)
        s.close()
        r = self.reopen()
        self.assertFalse(self.settle(r, intent))
        self.assertEqual(len(r.receipts), 1)

    def test_receipts_reject_foreign_runtime_identity(self):
        s = self.create()
        intent = s.poll(2)
        for identity in [intent.transition.transition_id.replace("world:", "foreign:", 1),
                         intent.transition.transition_id.replace(":run:", ":other:", 1),
                         intent.transition.transition_id.split(":", 2)[2], "unknown"]:
            with self.subTest(identity=identity), self.assertRaises(ValueError):
                s.acknowledge(identity, "APPLIED", "witness", 2)
        self.assertEqual(s.next_index, 0)

    def test_outcomes_require_correct_timing_and_evidence(self):
        s = self.create()
        intent = s.poll(2)
        for outcome, evidence, tick in [("APPLIED", "witness", 3), ("APPLIED", "witness", None),
                                       ("APPLIED", "", 2), ("APPLIED", "witness", True),
                                       ("MISSED", "witness", None), ("NOT_APPLIED", "witness", None),
                                       ("FAILED", "witness", 2), ("other", "witness", None)]:
            with self.subTest(outcome=outcome, evidence=evidence, tick=tick), self.assertRaises(ValueError):
                s.acknowledge(intent.transition.transition_id, outcome, evidence, tick)
        s.acknowledge(intent.transition.transition_id, "FAILED", "failed-witness")
        late = s.poll(8)
        for outcome in ["APPLIED", "FAILED"]:
            with self.assertRaises(ValueError):
                s.acknowledge(late.transition.transition_id, outcome, "witness", 5 if outcome == "APPLIED" else None)
        s.acknowledge(late.transition.transition_id, "MISSED", "missed-witness")

    def test_immutable_views_and_binding(self):
        s = self.create()
        intent = s.poll(2)
        with self.assertRaises(FrozenInstanceError):
            intent.observed_tick = 9
        with self.assertRaises(FrozenInstanceError):
            s.schedule.events = ()
        for name, value in [("schedule", Schedule([])), ("world_id", "foreign"), ("run_id", "foreign")]:
            with self.subTest(name=name), self.assertRaises(AttributeError):
                setattr(s, name, value)
        self.assertIsInstance(s.receipts, tuple)

    def test_distinct_create_open_and_no_v1_admission(self):
        with self.assertRaises(FileNotFoundError):
            self.reopen()
        s = self.create()
        with self.assertRaises((ValueError, FileExistsError)):
            self.create()
        s.close()
        with self.assertRaises(FileExistsError):
            self.create()
        self.path.write_text('{"version":1,"cursor":2}\n')
        with self.assertRaises(ValueError):
            self.reopen()

    def test_foreign_bindings_rejected_without_repair(self):
        self.create().close()
        original = self.path.read_bytes()
        for world, run, events in [("other", "run", self.events), ("world", "other", self.events),
                                  ("world", "run", [])]:
            with self.subTest(world=world, run=run, events=events), self.assertRaises(ValueError):
                self.reopen(events, world, run)
        self.assertEqual(self.path.read_bytes(), original)

    def test_torn_and_corrupt_frames_fail_closed(self):
        s = self.create()
        s.poll(2)
        s.close()
        good = self.path.read_bytes()
        for damaged in [b"", good[:-1], good[:-12], good + b"partial", good.replace(b"PREPARE", b"PREPARX")]:
            with self.subTest(size=len(damaged)):
                self.path.write_bytes(damaged)
                with self.assertRaises(ValueError):
                    self.reopen()
                self.assertEqual(self.path.read_bytes(), damaged)

    def test_semantically_impossible_valid_checksum_history_rejected(self):
        self.create().close()
        header = self.path.read_bytes()
        previous = header.decode().strip().split("\t")[-1]
        for operation in ["CLOCK\t2", "PREPARE\t1\t2", "PREPARE\t0\t1",
                          "PREPARE\t00\t2", "ACK\t0\tAPPLIED\t2\twitness", "BOGUS\t0"]:
            payload = f"1\t{previous}\t{operation}".encode()
            forged = header + payload + b"\t" + hashlib.sha256(payload).hexdigest().encode() + b"\n"
            self.path.write_bytes(forged)
            with self.subTest(operation=operation), self.assertRaises(ValueError):
                self.reopen()

    def test_short_writes_complete_valid_record(self):
        s = self.create()
        real = s._write
        s._write = lambda data: real(data[:3])
        s.poll(2)
        s.close()
        self.assertTrue(self.reopen().pending.recovery_required)

    def test_failed_append_poison_and_no_lost_intent(self):
        s = self.create()
        s._write = lambda data: (_ for _ in ()).throw(OSError("injected before write"))
        with self.assertRaises(OSError):
            s.poll(2)
        with self.assertRaises(ValueError):
            s.poll(2)
        s.close()
        r = self.reopen()
        self.assertIsNone(r.pending)
        self.assertTrue(r.poll(2).executable)

    def test_partial_append_poison_and_reopen_rejected(self):
        s = self.create()
        real = s._write
        first = True
        def torn(data):
            nonlocal first
            if first:
                first = False
                return real(data[:9])
            raise OSError("injected torn append")
        s._write = torn
        with self.assertRaises(OSError):
            s.poll(2)
        s.close()
        damaged = self.path.read_bytes()
        with self.assertRaises(ValueError):
            self.reopen()
        self.assertEqual(self.path.read_bytes(), damaged)

    def test_zero_progress_write_poison(self):
        s = self.create()
        s._write = lambda data: 0
        with self.assertRaises(OSError):
            s.poll(2)
        with self.assertRaises(ValueError):
            s.poll(2)

    def test_force_failure_after_intent_holds_on_reopen(self):
        s = self.create()
        s._force = lambda: (_ for _ in ()).throw(OSError("injected uncertain force"))
        with self.assertRaises(OSError):
            s.poll(2)
        with self.assertRaises(ValueError):
            s.poll(2)
        s.close()
        r = self.reopen()
        self.assertTrue(r.pending.recovery_required)
        self.assertFalse(r.pending.executable)

    def test_force_failure_after_receipt_does_not_duplicate(self):
        s = self.create()
        intent = s.poll(2)
        s._force = lambda: (_ for _ in ()).throw(OSError("injected receipt force"))
        with self.assertRaises(OSError):
            self.settle(s, intent)
        s.close()
        r = self.reopen()
        self.assertIsNone(r.pending)
        self.assertFalse(self.settle(r, intent))
        self.assertEqual(r.next_index, 1)

    def test_creation_directory_sync_failure_returns_no_executor(self):
        with patch.object(Scheduler, "_force_parent", side_effect=OSError("injected directory force")):
            with self.assertRaises(OSError):
                self.create()
        self.assertIsNone(self.reopen().pending)

    def test_capacity_exhaustion_precedes_intent(self):
        s = self.create()
        with patch("event_scheduler.MAX_RECORDS", 1):
            with self.assertRaises(ValueError):
                s.poll(2)
        self.assertIsNone(s.pending)
        self.assertEqual(s.cursor, -1)
        with patch("event_scheduler.MAX_FILE_BYTES", os.fstat(s._fd).st_size):
            with self.assertRaises(ValueError):
                s.poll(2)
        self.assertTrue(s.poll(2).executable)

    def test_prepare_reserves_a_receipt_record(self):
        s = self.create()
        size = os.fstat(s._fd).st_size
        with patch("event_scheduler.MAX_RECORDS", 2):
            with self.assertRaises(ValueError):
                s.poll(2)
            self.assertEqual(os.fstat(s._fd).st_size, size)
            self.assertIsNone(s.pending)
        with patch("event_scheduler.MAX_RECORDS", 3):
            intent = s.poll(2)
            self.assertTrue(self.settle(s, intent))
            self.assertEqual(s.next_index, 1)

    def test_prepare_reserves_bytes_for_reconciliation_after_reopen(self):
        s = self.create()
        size = os.fstat(s._fd).st_size
        with patch("event_scheduler.MAX_FILE_BYTES", size + 1024):
            with self.assertRaises(ValueError):
                s.poll(2)
            self.assertEqual(os.fstat(s._fd).st_size, size)
        with patch("event_scheduler.MAX_FILE_BYTES", size + 2048):
            identity = s.poll(2).transition.transition_id
            s.close()
            r = self.reopen()
            self.assertTrue(r.reconcile(identity, "NOT_APPLIED", "witness"))
            self.assertEqual(r.next_index, 1)

    def test_forked_handle_rejected_before_inherited_mutex(self):
        s = self.create()
        acquired, release = threading.Event(), threading.Event()
        def hold():
            with s._mutex:
                acquired.set()
                release.wait(10)
        thread = threading.Thread(target=hold)
        thread.start()
        self.assertTrue(acquired.wait(5))
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", DeprecationWarning)
                child = os.fork()
            if child == 0:
                signal.alarm(3)
                for action in [lambda: s.poll(2), s.close,
                               lambda: Scheduler.open(self.path, self.events, "world", "run")]:
                    try:
                        action()
                    except JournalError:
                        continue
                    os._exit(1)
                os._exit(23)
            _, status = os.waitpid(child, 0)
            self.assertEqual(os.waitstatus_to_exitcode(status), 23)
        finally:
            release.set()
            thread.join(5)
        self.assertTrue(s.poll(2).executable)

    def test_process_kill_at_each_delivery_boundary(self):
        # Synthetic durable counter is a crash witness, not a Minecraft effect.
        script = r'''
import os, signal, sys
from event_scheduler import Event, Scheduler
path, marker, phase = sys.argv[1:]
s = Scheduler.create(path, [Event("a", "crop_failure", 2, 3, .4)], "world", "run")
def die(): os.kill(os.getpid(), signal.SIGKILL)
if phase == "before_intent": die()
i = s.poll(2)
if phase == "after_intent": die()
with open(marker, "w") as f:
    f.write("1")
    f.flush()
    os.fsync(f.fileno())
if phase == "after_effect": die()
s.acknowledge(i.transition.transition_id, "APPLIED", "physical-witness", 2)
die()
'''
        for phase in ["before_intent", "after_intent", "after_effect", "after_receipt"]:
            with self.subTest(phase=phase):
                path = Path(self.temp.name) / f"{phase}.journal"
                marker = Path(self.temp.name) / f"{phase}.effect"
                child = subprocess.run([sys.executable, "-c", script, str(path), str(marker), phase],
                                       cwd=Path(__file__).parent, capture_output=True, text=True, timeout=15)
                self.assertEqual(child.returncode, -signal.SIGKILL, child.stderr)
                with Scheduler.open(path, self.events, "world", "run") as r:
                    if phase == "before_intent":
                        self.assertIsNone(r.pending)
                        self.assertTrue(r.poll(2).executable)
                    elif phase in ("after_intent", "after_effect"):
                        self.assertFalse(r.pending.executable)
                        with self.assertRaises(ValueError):
                            r.poll(2)
                        identity = r.pending.transition.transition_id
                        r.reconcile(identity, "APPLIED" if phase == "after_effect" else "NOT_APPLIED",
                                    "physical-witness", 2 if phase == "after_effect" else None)
                        self.assertIsNone(r.poll(2))
                    else:
                        self.assertIsNone(r.pending)
                        self.assertEqual(r.next_index, 1)
                        self.assertIsNone(r.poll(2))
                self.assertEqual(marker.read_text() if marker.exists() else "0",
                                 "1" if phase in ("after_effect", "after_receipt") else "0")


if __name__ == "__main__":
    unittest.main(verbosity=2)
