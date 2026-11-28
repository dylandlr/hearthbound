"""Durable experiment intents, NOT a Minecraft effect executor.

Protocol and limits: docs/C14_EVENT_SCHEDULER_CONTRACT.md. Linux local filesystems
only. Reopened pending intents require external reconciliation, never replay.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import fcntl
import hashlib
import math
import os
from pathlib import Path
import re
import stat
import struct
import threading

TYPES = frozenset({"crop_failure", "mill_failure", "specialist_loss",
                   "resource_depletion", "communication_failure", "demand_change"})
MAX_TICK = (1 << 63) - 1
MAX_EVENTS = 4096
MAX_LINE_BYTES = 1024
MAX_RECORDS = 100000
MAX_FILE_BYTES = 16 * 1024 * 1024
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z", re.ASCII)
_INTEGER = re.compile(r"(?:0|[1-9][0-9]*)\Z", re.ASCII)
_HASH = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
_OWNERS: set[tuple[int, int]] = set()
_OWNER_LOCK = threading.RLock()
_IMPORT_PID = os.getpid()


class JournalError(ValueError):
    """Invalid state, binding, history, or use of an unhealthy journal."""


def _token(value: str) -> str:
    if type(value) is not str or not _TOKEN.fullmatch(value):
        raise JournalError("invalid ASCII identity")
    return value


def _tick(value: int) -> int:
    if type(value) is not int or not 0 <= value <= MAX_TICK:
        raise JournalError("tick must be a nonnegative signed 64-bit integer")
    return value


def _decimal(value: str) -> int:
    if not _INTEGER.fullmatch(value) or len(value) > 19:
        raise JournalError("noncanonical integer")
    return _tick(int(value))


@dataclass(frozen=True)
class Event:
    event_id: str
    kind: str
    onset: int
    duration: int
    severity: float

    def __post_init__(self):
        _token(self.event_id)
        if type(self.kind) is not str or self.kind not in TYPES:
            raise JournalError("unsupported event kind")
        _tick(self.onset)
        _tick(self.duration)
        if self.duration == 0 or self.duration > MAX_TICK - self.onset:
            raise JournalError("invalid interval or end-tick overflow")
        if (type(self.severity) not in (int, float)
                or not 0 <= self.severity <= 1 or not math.isfinite(self.severity)):
            raise JournalError("severity must be finite in [0, 1]")
        object.__setattr__(self, "severity", 0.0 if self.severity == 0 else float(self.severity))


@dataclass(frozen=True)
class Transition:
    transition_id: str
    event_id: str
    phase: str
    tick: int
    kind: str
    severity: float


@dataclass(frozen=True, init=False)
class Schedule:
    events: tuple[Event, ...]
    digest: str
    timeline: tuple[Transition, ...]

    def __init__(self, events):
        # Bound even a generator instead of materializing an unbounded iterable.
        collected = []
        for event in events:
            if not isinstance(event, Event) or len(collected) >= MAX_EVENTS:
                raise JournalError("invalid event or schedule capacity exceeded")
            collected.append(event)
        ordered = tuple(sorted(collected, key=lambda event: event.event_id))
        if len({event.event_id for event in ordered}) != len(ordered):
            raise JournalError("duplicate event identity")
        canonical = "hearthbound:event-schedule:v2\n" + "".join(
            f"{e.event_id}\t{e.kind}\t{e.onset}\t{e.duration}\t"
            f"{struct.pack('>d', e.severity).hex()}\n" for e in ordered)
        digest = hashlib.sha256(canonical.encode("ascii")).hexdigest()
        transitions = [Transition(f"{digest}:{e.event_id}:{phase}", e.event_id,
                                  phase, tick, e.kind, e.severity)
                       for e in ordered
                       for phase, tick in (("start", e.onset), ("end", e.onset + e.duration))]
        object.__setattr__(self, "events", ordered)
        object.__setattr__(self, "digest", digest)
        object.__setattr__(self, "timeline", tuple(sorted(
            transitions, key=lambda t: (t.tick, 0 if t.phase == "end" else 1, t.event_id))))


@dataclass(frozen=True)
class Intent:
    index: int
    transition: Transition
    observed_tick: int
    recovery_required: bool = False

    @property
    def executable(self) -> bool:
        return not self.recovery_required and self.observed_tick == self.transition.tick


@dataclass(frozen=True)
class Receipt:
    index: int
    transition_id: str
    mode: str
    outcome: str
    effect_tick: int | None
    evidence_id: str


@dataclass(frozen=True)
class _Plan:
    cursor: int
    next_index: int
    pending: Intent | None
    receipt: Receipt | None = None


class Scheduler:
    """Single writer; durable intent first, explicit receipt second.

    No callback here can mutate the world. An APPLIED receipt remains the
    adapter's claim until a native independent witness validates it.
    """

    def __init__(self, path, events, world_id, run_id, *, _create):
        if os.getpid() != _IMPORT_PID:
            raise JournalError("forked processes must exec before using scheduler journals")
        self._pid = os.getpid()
        self._schedule = events if isinstance(events, Schedule) else Schedule(events)
        self._world_id, self._run_id = _token(world_id), _token(run_id)
        self.path = Path(path).absolute()
        self._mutex = threading.RLock()
        self._fd = None
        self._owner = None
        self._closed = False
        self._poisoned = False
        self._cursor = -1
        self._next_index = 0
        self._pending = None
        self._receipts: dict[str, Receipt] = {}
        self._records = 0
        self._size = 0
        self._previous = "0" * 64
        # POSIX process locks are released when ANY descriptor on the inode is
        # closed. Reject a second local handle BEFORE opening its descriptor.
        with _OWNER_LOCK:
            try:
                before = self.path.stat(follow_symlinks=False)
            except FileNotFoundError:
                before = None
            if before is not None and (before.st_dev, before.st_ino) in _OWNERS:
                raise JournalError("journal already open in this process")
            flags = os.O_RDWR | os.O_NOFOLLOW
            if _create:
                flags |= os.O_CREAT | os.O_EXCL
            try:
                self._fd = os.open(self.path, flags, 0o600)
                identity = os.fstat(self._fd)
                if not stat.S_ISREG(identity.st_mode):
                    raise JournalError("journal must be a regular file")
                self._owner = (identity.st_dev, identity.st_ino)
                fcntl.lockf(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                _OWNERS.add(self._owner)
                if _create:
                    self._append("BIND", [self.world_id, self.run_id, self.schedule.digest], None)
                    self._force_parent()
                else:
                    self._recover()
            except BaseException:
                self._poisoned = True
                self.close()
                raise

    @classmethod
    def create(cls, path, events, world_id, run_id):
        return cls(path, events, world_id, run_id, _create=True)

    @classmethod
    def open(cls, path, events, world_id, run_id):
        return cls(path, events, world_id, run_id, _create=False)

    @property
    def schedule(self):
        return self._schedule

    @property
    def world_id(self):
        return self._world_id

    @property
    def run_id(self):
        return self._run_id

    def _healthy(self):
        self._same_process()
        if self._closed or self._poisoned:
            raise JournalError("journal is closed or has an uncertain write; reopen and reconcile")

    def _same_process(self):
        # Check BEFORE acquiring a possibly inherited RLock. POSIX file locks
        # belong to the parent process and are not inherited with this object.
        if os.getpid() != self._pid:
            raise JournalError("inherited scheduler handles cannot be used after fork; exec first")

    @property
    def cursor(self):
        self._same_process()
        with self._mutex:
            self._healthy()
            return self._cursor

    @property
    def next_index(self):
        self._same_process()
        with self._mutex:
            self._healthy()
            return self._next_index

    @property
    def pending(self):
        self._same_process()
        with self._mutex:
            self._healthy()
            return self._pending

    @property
    def receipts(self):
        self._same_process()
        with self._mutex:
            self._healthy()
            return tuple(self._receipts.values())

    def poll(self, tick):
        self._same_process()
        with self._mutex:
            self._healthy()
            _tick(tick)
            if tick < self._cursor:
                raise JournalError("backward clock")
            if self._pending is not None:
                raise JournalError("outstanding intent must be settled; it is never reissued")
            if (self._next_index < len(self.schedule.timeline)
                    and self.schedule.timeline[self._next_index].tick <= tick):
                args = [str(self._next_index), str(tick)]
                self._append("PREPARE", args, self._plan("PREPARE", args))
                return self._pending
            if tick > self._cursor:
                args = [str(tick)]
                self._append("CLOCK", args, self._plan("CLOCK", args))
            return None

    def acknowledge(self, transition_id, outcome, evidence_id, effect_tick=None):
        return self._settle("ACK", transition_id, outcome, evidence_id, effect_tick)

    def reconcile(self, transition_id, outcome, evidence_id, effect_tick=None):
        return self._settle("RECONCILE", transition_id, outcome, evidence_id, effect_tick)

    def _settle(self, mode, transition_id, outcome, evidence_id, effect_tick):
        self._same_process()
        with self._mutex:
            self._healthy()
            _token(evidence_id)
            if effect_tick is not None:
                _tick(effect_tick)
            if type(transition_id) is not str or type(outcome) is not str:
                raise JournalError("invalid receipt identity or outcome")
            prior = self._receipts.get(transition_id)
            if prior is not None:
                candidate = Receipt(prior.index, transition_id, mode, outcome, effect_tick, evidence_id)
                if candidate != prior:
                    raise JournalError("conflicting duplicate receipt")
                return False
            if self._pending is None or transition_id != self._pending.transition.transition_id:
                raise JournalError("unknown or foreign transition")
            if (mode == "RECONCILE") != self._pending.recovery_required:
                raise JournalError("reopened intents require reconciliation; live intents require acknowledgement")
            args = [str(self._pending.index), outcome,
                    "-" if effect_tick is None else str(effect_tick), evidence_id]
            self._append(mode, args, self._plan(mode, args))
            return True

    def _plan(self, op, args):
        """Validate both live requests and replay before installing any state."""
        if op == "CLOCK" and len(args) == 1:
            tick = _decimal(args[0])
            if (tick <= self._cursor or self._pending is not None
                    or (self._next_index < len(self.schedule.timeline)
                        and self.schedule.timeline[self._next_index].tick <= tick)):
                raise JournalError("clock bypasses due transition or pending intent")
            return _Plan(tick, self._next_index, None)
        if op == "PREPARE" and len(args) == 2:
            index, tick = map(_decimal, args)
            if (index != self._next_index or index >= len(self.schedule.timeline)
                    or self._pending is not None or tick < self._cursor
                    or self.schedule.timeline[index].tick > tick):
                raise JournalError("impossible intent history")
            transition = self.schedule.timeline[index]
            bound_transition = replace(
                transition, transition_id=f"{self.world_id}:{self.run_id}:{transition.transition_id}")
            return _Plan(tick, index, Intent(index, bound_transition, tick))
        if op in ("ACK", "RECONCILE") and len(args) == 4:
            index = _decimal(args[0])
            outcome, raw_effect, evidence = args[1:]
            effect_tick = None if raw_effect == "-" else _decimal(raw_effect)
            _token(evidence)
            pending = self._pending
            if pending is None or index != pending.index:
                raise JournalError("receipt does not settle the outstanding intent")
            on_time = pending.observed_tick == pending.transition.tick
            if outcome == "APPLIED":
                valid = on_time and effect_tick == pending.transition.tick
            elif outcome == "FAILED":
                valid = on_time and effect_tick is None
            elif outcome == "MISSED":
                valid = not on_time and effect_tick is None
            elif outcome == "NOT_APPLIED":
                valid = op == "RECONCILE" and effect_tick is None
            else:
                valid = False
            if not valid:
                raise JournalError("outcome contradicts delivery timing or settlement mode")
            receipt = Receipt(index, pending.transition.transition_id, op, outcome, effect_tick, evidence)
            return _Plan(self._cursor, index + 1, None, receipt)
        raise JournalError("invalid journal operation or field count")

    def _install(self, plan):
        self._cursor, self._next_index, self._pending = plan.cursor, plan.next_index, plan.pending
        if plan.receipt is not None:
            self._receipts[plan.receipt.transition_id] = plan.receipt

    def _write(self, data):
        """One unbuffered write; replaceable in fault-injection tests."""
        return os.write(self._fd, data)

    def _force(self):
        os.fsync(self._fd)

    def _force_parent(self):
        parent = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)

    def _append(self, op, args, plan):
        payload = "\t".join([str(self._records), self._previous, op, *args]).encode("ascii")
        checksum = hashlib.sha256(payload).hexdigest()
        line = payload + b"\t" + checksum.encode("ascii") + b"\n"
        if (len(line) > MAX_LINE_BYTES or self._records >= MAX_RECORDS
                or self._size + len(line) > MAX_FILE_BYTES):
            raise JournalError("journal capacity exceeded")
        if op == "PREPARE" and (self._records + 2 > MAX_RECORDS
                or self._size + len(line) + MAX_LINE_BYTES > MAX_FILE_BYTES):
            raise JournalError("insufficient capacity for intent and its settlement")
        try:
            if os.fstat(self._fd).st_size != self._size:
                raise JournalError("journal changed outside its writer")
            os.lseek(self._fd, self._size, os.SEEK_SET)
            rest = memoryview(line)
            while rest:
                count = self._write(rest)
                if count <= 0:
                    raise OSError("journal write made no progress")
                rest = rest[count:]
            self._force()
            self._records += 1
            self._size += len(line)
            self._previous = checksum
            if plan is not None:
                self._install(plan)
        except BaseException:
            self._poisoned = True
            raise

    def _recover(self):
        size = os.fstat(self._fd).st_size
        if size == 0 or size > MAX_FILE_BYTES:
            raise JournalError("empty or oversized journal")
        data = bytearray()
        while len(data) <= MAX_FILE_BYTES:
            part = os.read(self._fd, min(65536, MAX_FILE_BYTES + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        if len(data) != size or not data.endswith(b"\n"):
            raise JournalError("torn or changing journal")
        if any(value not in (9, 10) and not 32 <= value <= 126 for value in data):
            raise JournalError("noncanonical journal byte")
        for line in data.splitlines(keepends=True):
            if len(line) > MAX_LINE_BYTES or self._records >= MAX_RECORDS:
                raise JournalError("journal capacity exceeded")
            try:
                fields = line[:-1].decode("ascii").split("\t")
            except UnicodeDecodeError as exc:
                raise JournalError("non-ASCII journal") from exc
            if len(fields) < 5 or not _HASH.fullmatch(fields[-1]):
                raise JournalError("malformed frame")
            sequence, previous, op, *args = fields[:-1]
            payload = "\t".join(fields[:-1]).encode("ascii")
            checksum = hashlib.sha256(payload).hexdigest()
            if (_decimal(sequence) != self._records or previous != self._previous
                    or checksum != fields[-1]):
                raise JournalError("broken journal sequence or checksum")
            if self._records == 0:
                if op != "BIND" or args != [self.world_id, self.run_id, self.schedule.digest]:
                    raise JournalError("foreign world, run, schedule, or journal version")
            else:
                self._install(self._plan(op, args))
            self._records += 1
            self._previous = checksum
            self._size += len(line)
        if self._pending is not None:
            self._pending = replace(self._pending, recovery_required=True)

    def close(self):
        self._same_process()
        with self._mutex, _OWNER_LOCK:
            if not self._closed:
                self._closed = True
                try:
                    if self._fd is not None:
                        os.close(self._fd)
                finally:
                    self._fd = None
                    if self._owner is not None:
                        _OWNERS.discard(self._owner)

    def __enter__(self):
        self._healthy()
        return self

    def __exit__(self, *exc):
        self.close()
