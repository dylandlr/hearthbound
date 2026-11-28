"""Independent C14 wire/behavior oracles across Python and Java; no Forge execution."""
from pathlib import Path
import hashlib
import os
import random
import select
import shutil
import struct
import subprocess
import tempfile
import unittest

from event_scheduler import Event, Schedule, Scheduler


ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests/fixtures/event_scheduler"
WORLD, RUN = "world-test", "run-test"
GOLDEN_DIGESTS = {
    "compound": "5ec486a64d4b3afd16ea1a006ce6cab85e38b46005fa4a6bd4d2eb990014deeb",
    "boundary": "fd092a0e44044f6c86d962b2fde642afbf2c49d863ff94da2e1b775f02a20a5a",
    "empty": "fa7f522fc086a008e3c1967439226cc27ad3d4d6ab9ecd04b0c46cc12ed4562b",
}
COMPOUND_ORDER = [
    (0, "start", "Alpha"), (1, "start", "z"), (2, "start", "tiny"),
    (3, "end", "Alpha"), (3, "end", "tiny"), (3, "start", "alpha"),
    (5, "end", "alpha"), (5, "end", "z"),
]


def read_events(path):
    result = []
    for line in Path(path).read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        identity, kind, onset, duration, severity = line.split("\t")
        result.append(Event(identity, kind, int(onset), int(duration), float(severity)))
    return result


def state_text(scheduler):
    lines = [f"DIGEST\t{scheduler.schedule.digest}", f"CLOCK\t{scheduler.cursor}",
             f"NEXT\t{scheduler.next_index}"]
    pending = scheduler.pending
    if pending is None:
        lines.append("PENDING\t-")
    else:
        transition = pending.transition
        lines.append("\t".join(map(str, ["PENDING", pending.index, transition.transition_id,
                     transition.phase, transition.tick, pending.observed_tick, transition.kind,
                     struct.pack(">d", transition.severity).hex(),
                     str(pending.recovery_required).lower()])))
    for receipt in scheduler.receipts:
        lines.append("\t".join(map(str, ["RECEIPT", receipt.index, receipt.transition_id,
                     receipt.outcome, receipt.evidence_id,
                     "-" if receipt.effect_tick is None else receipt.effect_tick, receipt.mode])))
    return "\n".join(lines) + "\n"


def framed_history(digest, operations, world=WORLD, run=RUN):
    """Construct valid checksums around potentially impossible histories, outside either runtime."""
    previous = "0" * 64
    frames = []
    for sequence, fields in enumerate([("BIND", world, run, digest), *operations]):
        payload = "\t".join([str(sequence), previous, *map(str, fields)])
        previous = hashlib.sha256(payload.encode("ascii")).hexdigest()
        frames.append(f"{payload}\t{previous}\n")
    return "".join(frames).encode("ascii")


class EventSchedulerParityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.java_exe = shutil.which("java")
        if not cls.java_exe:
            raise RuntimeError("Java 17+ is required for scheduler parity")
        cls.output = None
        cls.classpath = os.environ.get("HEARTHBOUND_EVENT_JAVA_CLASSPATH")
        if not cls.classpath:
            cls.output = tempfile.TemporaryDirectory(prefix="hearthbound-parity-")
            cls.classpath = cls.output.name
            javac = shutil.which("javac")
            compiler = [javac] if javac else [cls.java_exe, "--module", "jdk.compiler/com.sun.tools.javac.Main"]
            sources = sorted((ROOT / "src/main/java/dev/hearthbound/experiment").glob("*.java"))
            sources += sorted((ROOT / "src/test/java/dev/hearthbound/experiment").glob("*.java"))
            subprocess.run(compiler + ["--release", "17", "-encoding", "UTF-8", "-d", cls.classpath]
                           + [str(p) for p in sources], check=True, cwd=ROOT)

    @classmethod
    def tearDownClass(cls):
        if cls.output is not None:
            cls.output.cleanup()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="hearthbound-parity-case-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.fixture = FIXTURES / "compound.tsv"
        self.events = read_events(self.fixture)
        self.schedule = Schedule(self.events)

    def command(self, *args):
        return [self.java_exe, "-cp", self.classpath,
                "dev.hearthbound.experiment.EventSchedulerCli", *map(str, args)]

    def java(self, *args, success=True):
        result = subprocess.run(self.command(*args), text=True, capture_output=True, timeout=15, cwd=ROOT)
        if success:
            self.assertEqual(0, result.returncode, result.stderr)
        else:
            self.assertNotEqual(0, result.returncode, result.stdout)
        return result.stdout

    def assert_rejected_both(self, path, fixture=None, world=WORLD, run=RUN):
        fixture = fixture or self.fixture
        before = path.read_bytes()
        with self.assertRaises((ValueError, OSError)):
            with Scheduler.open(path, read_events(fixture), world, run):
                self.fail("malformed history was accepted")
        self.java("status", path, fixture, world, run, success=False)
        self.assertEqual(before, path.read_bytes(), "rejection must not repair or truncate evidence")

    def complete_python(self, path, events, ticks):
        transitions = []
        with Scheduler.create(path, events, WORLD, RUN) as scheduler:
            for tick in ticks:
                while (intent := scheduler.poll(tick)) is not None:
                    transition = intent.transition
                    transitions.append((transition.tick, transition.phase, transition.event_id))
                    outcome = "APPLIED" if intent.executable else "MISSED"
                    scheduler.acknowledge(transition.transition_id, outcome, f"witness-{intent.index}",
                                          tick if intent.executable else None)
            text = state_text(scheduler)
        return transitions, text

    def script(self, events, ticks):
        schedule = Schedule(events)
        index = 0
        operations = []
        for tick in ticks:
            while index < len(schedule.timeline) and schedule.timeline[index].tick <= tick:
                transition = schedule.timeline[index]
                outcome = "APPLIED" if transition.tick == tick else "MISSED"
                effect_tick = str(tick) if outcome == "APPLIED" else "-"
                operations.extend([f"POLL\t{tick}",
                                   f"ACK\t@{index}\t{outcome}\twitness-{index}\t{effect_tick}"])
                index += 1
            operations.append(f"POLL\t{tick}")
        path = self.directory / "commands.tsv"
        path.write_text("\n".join(operations) + "\n")
        return path

    def test_fixed_digest_oracles_and_negative_zero_normalization(self):
        # These fixed hashes use explicit binary64 bit patterns, not implementation helpers.
        for name, expected in GOLDEN_DIGESTS.items():
            with self.subTest(name=name):
                fixture = FIXTURES / f"{name}.tsv"
                events = read_events(fixture)
                self.assertEqual(expected, Schedule(events).digest)
                self.assertEqual(expected, Schedule(reversed(events)).digest)
                self.assertEqual(expected, self.java("digest", fixture).strip())
        positive = [Event(e.event_id, e.kind, e.onset, e.duration, abs(e.severity)) for e in self.events]
        self.assertEqual(self.schedule.digest, Schedule(positive).digest)

    def test_compound_boundaries_end_before_start_and_identical_journal_bytes(self):
        ticks = [0, 1, 2, 3, 4, 5, 6]
        py_path, java_path = self.directory / "python.log", self.directory / "java.log"
        order, expected = self.complete_python(py_path, self.events, ticks)
        self.assertEqual(COMPOUND_ORDER, order)
        actual = self.java("script", java_path, self.fixture, WORLD, RUN, self.script(self.events, ticks))
        self.assertEqual(expected, actual)
        self.assertEqual(py_path.read_bytes(), java_path.read_bytes())
        self.assertEqual(expected, self.java("status", py_path, self.fixture, WORLD, RUN))
        with Scheduler.open(java_path, self.events, WORLD, RUN) as scheduler:
            self.assertEqual(expected, state_text(scheduler))

    def test_skipped_ticks_have_missed_receipts_without_execution(self):
        py_path, java_path = self.directory / "python.log", self.directory / "java.log"
        order, expected = self.complete_python(py_path, self.events, [10])
        self.assertEqual(COMPOUND_ORDER, order)
        actual = self.java("script", java_path, self.fixture, WORLD, RUN, self.script(self.events, [10]))
        self.assertEqual(expected, actual)
        self.assertEqual(py_path.read_bytes(), java_path.read_bytes())
        with Scheduler.open(java_path, self.events, WORLD, RUN) as scheduler:
            self.assertTrue(all(r.outcome == "MISSED" and r.effect_tick is None for r in scheduler.receipts))

    def test_python_intent_is_held_and_reconciled_by_java(self):
        path = self.directory / "pending.log"
        with Scheduler.create(path, self.events, WORLD, RUN) as scheduler:
            intent = scheduler.poll(0)
            identity = intent.transition.transition_id
        with Scheduler.open(path, self.events, WORLD, RUN) as scheduler:
            self.assertTrue(scheduler.pending.recovery_required)
            self.assertFalse(scheduler.pending.executable)
            expected = state_text(scheduler)
        self.assertEqual(expected, self.java("status", path, self.fixture, WORLD, RUN))
        before = path.read_bytes()
        self.java("poll", path, self.fixture, WORLD, RUN, 0, success=False)
        self.assertEqual(before, path.read_bytes())
        actual = self.java("reconcile", path, self.fixture, WORLD, RUN,
                           identity, "NOT_APPLIED", "inspected-no-effect", "-")
        with Scheduler.open(path, self.events, WORLD, RUN) as scheduler:
            self.assertEqual(actual, state_text(scheduler))
            self.assertEqual((1, "RECONCILE", "NOT_APPLIED"),
                             (scheduler.next_index, scheduler.receipts[0].mode, scheduler.receipts[0].outcome))
            next_intent = scheduler.poll(1)
            self.assertEqual("z", next_intent.transition.event_id)

    def test_java_intent_is_held_and_reconciled_by_python(self):
        path = self.directory / "pending.log"
        commands = self.directory / "commands.tsv"
        commands.write_text("POLL\t0\nACK\t@0\tAPPLIED\twitness-0\t0\nPOLL\t1\n")
        self.java("script", path, self.fixture, WORLD, RUN, commands)
        with Scheduler.open(path, self.events, WORLD, RUN) as scheduler:
            self.assertEqual(1, scheduler.next_index)
            intent = scheduler.pending
            self.assertTrue(intent.recovery_required)
            self.assertFalse(intent.executable)
            scheduler.reconcile(intent.transition.transition_id, "APPLIED", "inspected-effect", 1)
            expected = state_text(scheduler)
        self.assertEqual(expected, self.java("status", path, self.fixture, WORLD, RUN))

    def test_reconciliation_retry_is_idempotent_but_conflicting_receipt_is_rejected(self):
        path = self.directory / "pending.log"
        with Scheduler.create(path, self.events, WORLD, RUN) as scheduler:
            identity = scheduler.poll(0).transition.transition_id
        self.java("reconcile", path, self.fixture, WORLD, RUN, identity, "APPLIED", "witness", 0)
        before = path.read_bytes()
        self.java("reconcile", path, self.fixture, WORLD, RUN, identity, "APPLIED", "witness", 0)
        self.java("reconcile", path, self.fixture, WORLD, RUN, identity, "APPLIED", "other", 0, success=False)
        with Scheduler.open(path, self.events, WORLD, RUN) as scheduler:
            self.assertFalse(scheduler.reconcile(identity, "APPLIED", "witness", 0))
            with self.assertRaises(ValueError):
                scheduler.reconcile(identity, "FAILED", "witness")
        self.assertEqual(before, path.read_bytes())

    def test_signed_long_boundary_and_empty_control(self):
        for name, ticks in (("boundary", [(1 << 63) - 2, (1 << 63) - 1]), ("empty", [0, 123])):
            with self.subTest(name=name):
                fixture = FIXTURES / f"{name}.tsv"
                events = read_events(fixture)
                py_path, java_path = self.directory / f"{name}-py.log", self.directory / f"{name}-java.log"
                _, expected = self.complete_python(py_path, events, ticks)
                self.assertEqual(expected, self.java("script", java_path, fixture, WORLD, RUN,
                                                     self.script(events, ticks)))
                self.assertEqual(py_path.read_bytes(), java_path.read_bytes())

    def test_foreign_world_run_and_schedule_are_rejected_without_modification(self):
        path = self.directory / "binding.log"
        with Scheduler.create(path, self.events, WORLD, RUN):
            pass
        self.assert_rejected_both(path, world="different-world")
        self.assert_rejected_both(path, run="different-run")
        self.assert_rejected_both(path, fixture=FIXTURES / "empty.tsv")

    def test_corrupt_and_torn_histories_fail_closed(self):
        valid = framed_history(self.schedule.digest, [("PREPARE", 0, 0), ("ACK", 0, "APPLIED", 0, "witness")])
        for name, data in {
            "empty": b"", "torn-newline": valid[:-1], "torn-frame": valid[:-15],
            "bare-cr-between-frames": valid.replace(b"\n", b"\r", 1),
            "garbage": valid + b"garbage\n", "non-ascii": valid + b"\xff\n",
            "checksum": valid.replace(b"witness", b"changed"),
            "crlf": valid.replace(b"\n", b"\r\n"),
            "oversized-line": valid + b"x" * 1025 + b"\n",
        }.items():
            with self.subTest(name=name):
                path = self.directory / f"{name}.log"
                path.write_bytes(data)
                self.assert_rejected_both(path)

    def test_hash_valid_impossible_histories_fail_closed(self):
        prepare = ("PREPARE", 0, 0)
        cases = {
            "skip-due": [("CLOCK", 0)],
            "wrong-next": [("PREPARE", 1, 0)],
            "negative-time": [("PREPARE", 0, -1)],
            "double-pending": [prepare, ("PREPARE", 1, 1)],
            "clock-with-pending": [prepare, ("CLOCK", 1)],
            "no-intent": [("ACK", 0, "APPLIED", 0, "witness")],
            "wrong-index": [prepare, ("ACK", 1, "APPLIED", 0, "witness")],
            "effect-missing": [prepare, ("ACK", 0, "APPLIED", "-", "witness")],
            "effect-wrong-time": [prepare, ("ACK", 0, "APPLIED", 1, "witness")],
            "late-applied": [("PREPARE", 0, 1), ("ACK", 0, "APPLIED", 0, "witness")],
            "on-time-missed": [prepare, ("ACK", 0, "MISSED", "-", "witness")],
            "not-applied-ack": [prepare, ("ACK", 0, "NOT_APPLIED", "-", "witness")],
            "noncanonical-index": [("PREPARE", "00", 0)],
            "unknown-op": [("SKIP", 0)],
            "second-binding": [("BIND", WORLD, RUN, self.schedule.digest)],
            "empty-evidence": [prepare, ("ACK", 0, "FAILED", "-", "")],
            "duplicate-receipt": [prepare, ("ACK", 0, "APPLIED", 0, "witness"),
                                  ("ACK", 0, "APPLIED", 0, "witness")],
        }
        for name, operations in cases.items():
            with self.subTest(name=name):
                path = self.directory / f"{name}.log"
                path.write_bytes(framed_history(self.schedule.digest, operations))
                self.assert_rejected_both(path)

    def test_cross_language_lock_survives_rejected_duplicate_and_hardlink_open(self):
        path, alias = self.directory / "locked.log", self.directory / "alias.log"
        with Scheduler.create(path, self.events, WORLD, RUN):
            os.link(path, alias)
            for candidate in (path, alias):
                with self.assertRaises((ValueError, OSError)):
                    with Scheduler.open(candidate, self.events, WORLD, RUN):
                        self.fail("duplicate writer accepted")
                # POSIX locks disappear if the failed open carelessly closes a descriptor for this inode.
                self.java("status", path, self.fixture, WORLD, RUN, success=False)
        self.java("status", path, self.fixture, WORLD, RUN)
        process = subprocess.Popen(self.command("hold", path, self.fixture, WORLD, RUN),
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, cwd=ROOT)
        try:
            ready, _, _ = select.select([process.stdout], [], [], 10)
            self.assertTrue(ready, "Java lock holder did not become ready")
            self.assertEqual("LOCKED\n", process.stdout.readline())
            with self.assertRaises((ValueError, OSError)):
                with Scheduler.open(path, self.events, WORLD, RUN):
                    self.fail("Java-owned journal accepted a Python writer")
            self.assertIsNone(process.poll())
            process.communicate("\n", timeout=10)
            self.assertEqual(0, process.returncode)
        finally:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
        with Scheduler.open(path, self.events, WORLD, RUN):
            pass

    def test_seeded_mixed_schedules_have_identical_durable_histories(self):
        rng = random.Random(1401)
        for trial in range(6):
            events = [Event(f"event-{i}", rng.choice(["crop_failure", "mill_failure", "demand_change"]),
                            rng.randrange(0, 9), rng.randrange(1, 5), rng.choice([0.0, 0.1, 0.5, 1.0]))
                      for i in range(7)]
            rng.shuffle(events)
            fixture = self.directory / f"random-{trial}.tsv"
            fixture.write_text("".join(f"{e.event_id}\t{e.kind}\t{e.onset}\t{e.duration}\t{e.severity}\n"
                                       for e in events))
            # Gaps intentionally mix on-time and missed transitions in the same journal.
            ticks = [0, 2, 3, 7, 12]
            py_path, java_path = self.directory / f"random-{trial}-py.log", self.directory / f"random-{trial}-java.log"
            with self.subTest(trial=trial):
                _, expected = self.complete_python(py_path, events, ticks)
                self.assertEqual(expected, self.java("script", java_path, fixture, WORLD, RUN,
                                                     self.script(events, ticks)))
                self.assertEqual(py_path.read_bytes(), java_path.read_bytes())


if __name__ == "__main__":
    unittest.main()
