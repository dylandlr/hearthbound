"""Scenario-v1 seeded block-target plans; no world mutation, actor feed, or physical sham claim.

The immutable manifest binds the full configuration and latent choices. Journal
wrappers preserve the existing scheduler-v2 format while binding its run identity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import re
from types import MappingProxyType

from event_scheduler import Event, Schedule, Scheduler, MAX_EVENTS, MAX_TICK

MAX_SCOPES = 64
MAX_RULES = 64
MAX_TARGETS = 256
MAX_AXIS_SIZE = 256
MAX_SELECTED_TARGETS = 65536
MAX_CONFIG_BYTES = 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
PPM = 1_000_000
GENERATOR = "sha256-counter-rejection-v1"
BLOCK_KINDS = frozenset({"crop_failure", "mill_failure", "resource_depletion"})
MODES = frozenset({"treatment", "sham", "no_event"})
_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z", re.ASCII)
_DIMENSION = re.compile(r"[a-z0-9_.-]+:[a-z0-9_./-]+\Z", re.ASCII)
_NAT = re.compile(r"0|[1-9][0-9]*\Z", re.ASCII)
_SIGNED = re.compile(r"0|-?[1-9][0-9]*\Z", re.ASCII)


def _integer(value, minimum, maximum):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("integer outside scenario bounds")
    return value


def _token(value):
    if type(value) is not str or not _TOKEN.fullmatch(value):
        raise ValueError("invalid scenario identity")
    return value


def _bounded(values, limit, expected):
    result = []
    for value in values:
        if len(result) >= limit or not isinstance(value, expected):
            raise ValueError("invalid or excessive scenario entries")
        result.append(value)
    return tuple(result)


def _hash(value):
    return hashlib.sha256(value if isinstance(value, bytes) else value.encode("ascii")).hexdigest()


def _document(data, limit):
    if type(data) is not bytes or not data or len(data) > limit or not data.endswith(b"\n"):
        raise ValueError("invalid bounded scenario document")
    if any(byte not in (9, 10) and not 32 <= byte <= 126 for byte in data):
        raise ValueError("scenario documents require canonical ASCII/TAB/LF")
    return data.decode("ascii")


def _number(text, signed=False):
    pattern = _SIGNED if signed else _NAT
    if not pattern.fullmatch(text) or len(text) > (11 if signed else 19):
        raise ValueError("noncanonical scenario integer")
    return _integer(int(text), -(1 << 31) if signed else 0,
                    (1 << 31) - 1 if signed else MAX_TICK)


@dataclass(frozen=True, order=True)
class Position:
    x: int
    y: int
    z: int

    def __post_init__(self):
        for coordinate in (self.x, self.y, self.z):
            _integer(coordinate, -(1 << 31), (1 << 31) - 1)

    def wire(self):
        return f"{self.x}\t{self.y}\t{self.z}"


@dataclass(frozen=True)
class Scope:
    scope_id: str
    dimension: str
    minimum: Position
    maximum: Position
    targets: tuple[Position, ...]

    def __post_init__(self):
        _token(self.scope_id)
        if (type(self.dimension) is not str or len(self.dimension) > 128
                or not _DIMENSION.fullmatch(self.dimension)):
            raise ValueError("invalid dimension identifier")
        if not isinstance(self.minimum, Position) or not isinstance(self.maximum, Position):
            raise ValueError("explicit region coordinates required")
        for low, high in zip((self.minimum.x, self.minimum.y, self.minimum.z),
                             (self.maximum.x, self.maximum.y, self.maximum.z)):
            if not 1 <= high - low + 1 <= MAX_AXIS_SIZE:
                raise ValueError("invalid or excessive permitted region")
        targets = tuple(sorted(_bounded(self.targets, MAX_TARGETS, Position)))
        if not targets or len(set(targets)) != len(targets):
            raise ValueError("empty or duplicate target positions")
        for target in targets:
            if not (self.minimum.x <= target.x <= self.maximum.x
                    and self.minimum.y <= target.y <= self.maximum.y
                    and self.minimum.z <= target.z <= self.maximum.z):
                raise ValueError("target outside permitted region")
        object.__setattr__(self, "targets", targets)

    def _lines(self):
        return [f"SCOPE\t{self.scope_id}\t{self.dimension}\t{self.minimum.wire()}\t"
                f"{self.maximum.wire()}\t{len(self.targets)}", *[f"BLOCK\t{p.wire()}" for p in self.targets]]

    @property
    def digest(self):
        return _hash("hearthbound:scenario-scope:v1\n" + "\n".join(self._lines()) + "\n")


@dataclass(frozen=True)
class Rule:
    rule_id: str
    kind: str
    count: int
    onset_min: int
    onset_max: int
    duration_min: int
    duration_max: int
    severity_min_ppm: int
    severity_max_ppm: int
    targets_per_event: int
    scope_ids: tuple[str, ...]

    def __post_init__(self):
        _token(self.rule_id)
        if type(self.kind) is not str or self.kind not in BLOCK_KINDS:
            raise ValueError("scenario-v1 requires a supported block-scoped event kind")
        _integer(self.count, 1, MAX_EVENTS)
        _integer(self.onset_min, 0, MAX_TICK)
        _integer(self.onset_max, self.onset_min, MAX_TICK)
        _integer(self.duration_min, 1, MAX_TICK)
        _integer(self.duration_max, self.duration_min, MAX_TICK)
        if self.onset_max > MAX_TICK - self.duration_max:
            raise ValueError("worst-case event end overflows signed-long ticks")
        _integer(self.severity_min_ppm, 0, PPM)
        _integer(self.severity_max_ppm, self.severity_min_ppm, PPM)
        _integer(self.targets_per_event, 1, MAX_TARGETS)
        scopes = tuple(sorted(_token(value) for value in _bounded(self.scope_ids, MAX_SCOPES, str)))
        if not scopes or len(set(scopes)) != len(scopes):
            raise ValueError("empty or duplicate scope choices")
        object.__setattr__(self, "scope_ids", scopes)

    def _lines(self):
        return [f"RULE\t{self.rule_id}\t{self.kind}\t{self.count}\t{self.onset_min}\t{self.onset_max}\t"
                f"{self.duration_min}\t{self.duration_max}\t{self.severity_min_ppm}\t{self.severity_max_ppm}\t"
                f"{self.targets_per_event}\t{len(self.scope_ids)}", *[f"USE_SCOPE\t{s}" for s in self.scope_ids]]


@dataclass(frozen=True, init=False)
class Config:
    scopes: tuple[Scope, ...]
    rules: tuple[Rule, ...]
    canonical: bytes
    digest: str

    def __init__(self, scopes, rules):
        scopes = tuple(sorted(_bounded(scopes, MAX_SCOPES, Scope), key=lambda value: value.scope_id))
        rules = tuple(sorted(_bounded(rules, MAX_RULES, Rule), key=lambda value: value.rule_id))
        by_id = {scope.scope_id: scope for scope in scopes}
        if len(by_id) != len(scopes) or len({rule.rule_id for rule in rules}) != len(rules):
            raise ValueError("duplicate scope or rule identity")
        if sum(rule.count for rule in rules) > MAX_EVENTS:
            raise ValueError("too many planned events")
        if sum(rule.count * rule.targets_per_event for rule in rules) > MAX_SELECTED_TARGETS:
            raise ValueError("too many planned target selections")
        for rule in rules:
            for identity in rule.scope_ids:
                if identity not in by_id or len(by_id[identity].targets) < rule.targets_per_event:
                    raise ValueError("unknown scope or insufficient eligible targets")
        lines = ["hearthbound:scenario-config:v1", f"SCOPES\t{len(scopes)}"]
        for scope in scopes:
            lines.extend(scope._lines())
        lines.append(f"RULES\t{len(rules)}")
        for rule in rules:
            lines.extend(rule._lines())
        canonical = ("\n".join(lines) + "\n").encode("ascii")
        if len(canonical) > MAX_CONFIG_BYTES:
            raise ValueError("configuration byte capacity exceeded")
        for name, value in (("scopes", scopes), ("rules", rules), ("canonical", canonical), ("digest", _hash(canonical))):
            object.__setattr__(self, name, value)

    @classmethod
    def from_bytes(cls, data):
        reader = _Reader(data)
        if reader.raw() != "hearthbound:scenario-config:v1":
            raise ValueError("unsupported scenario configuration version")
        count = _integer(_number(reader.fields("SCOPES", 1)[0]), 0, MAX_SCOPES)
        scopes = []
        for _ in range(count):
            values = reader.fields("SCOPE", 9)
            target_count = _integer(_number(values[8]), 1, MAX_TARGETS)
            coordinates = [_number(value, signed=True) for value in values[2:8]]
            targets = [Position(*[_number(value, signed=True) for value in reader.fields("BLOCK", 3)])
                       for _ in range(target_count)]
            scopes.append(Scope(values[0], values[1], Position(*coordinates[:3]), Position(*coordinates[3:]), targets))
        count = _integer(_number(reader.fields("RULES", 1)[0]), 0, MAX_RULES)
        rules = []
        for _ in range(count):
            values = reader.fields("RULE", 11)
            scope_count = _integer(_number(values[10]), 1, MAX_SCOPES)
            identities = [reader.fields("USE_SCOPE", 1)[0] for _ in range(scope_count)]
            rules.append(Rule(values[0], values[1], *[_number(value) for value in values[2:10]], identities))
        if reader.index != len(reader.lines):
            raise ValueError("trailing scenario configuration records")
        config = cls(scopes, rules)
        if config.canonical != data:
            raise ValueError("scenario configuration is not canonical")
        return config


class _Reader:
    def __init__(self, data):
        self.lines = _document(data, MAX_CONFIG_BYTES).split("\n")[:-1]
        self.index = 0

    def raw(self):
        if self.index >= len(self.lines):
            raise ValueError("truncated scenario configuration")
        value = self.lines[self.index]
        self.index += 1
        return value

    def fields(self, tag, count):
        fields = self.raw().split("\t")
        if len(fields) != count + 1 or fields[0] != tag:
            raise ValueError("invalid scenario configuration record")
        return fields[1:]


def _draw(key, rule_id, ordinal, field_name, bound, digest=None):
    """Specified independent SHA counter stream; injectable digest only for rejection tests."""
    _integer(bound, 1, 1 << 63)
    digest = digest or (lambda message: hashlib.sha256(message).digest())
    limit = (1 << 256) - ((1 << 256) % bound)
    for attempt in range(1024):
        message = (f"hearthbound:scenario-draw:v1\n{key}\n{rule_id}\n{ordinal}\n{field_name}\n{attempt}\n").encode("ascii")
        raw = digest(message)
        if type(raw) is not bytes or len(raw) != 32:
            raise ValueError("invalid SHA-256 draw")
        value = int.from_bytes(raw, "big")
        if value < limit:
            return value % bound
    raise ValueError("deterministic draw rejection budget exhausted")


@dataclass(frozen=True)
class Choice:
    rule_id: str
    ordinal: int
    pair_id: str
    kind: str
    scope: Scope
    targets: tuple[Position, ...]
    target_digest: str
    onset: int
    duration: int
    intended_ppm: int
    effective_ppm: int | None
    event: Event | None


@dataclass(frozen=True, init=False)
class Scenario:
    config: Config
    seed: int
    mode: str
    trial_id: str
    sampling_key: str
    choices: tuple[Choice, ...]
    schedule: Schedule
    manifest: bytes
    manifest_digest: str
    journal_run_id: str
    _by_event: object = field(repr=False, compare=False)

    def __init__(self, config, seed, mode, trial_id):
        if not isinstance(config, Config):
            raise ValueError("validated scenario configuration required")
        _integer(seed, 0, MAX_TICK)
        if type(mode) is not str or mode not in MODES:
            raise ValueError("invalid scenario mode")
        _token(trial_id)
        sampling_key = _hash(f"hearthbound:scenario-sampling:v1\n{config.digest}\n{seed}\n")
        context = _hash(f"hearthbound:scenario-context:v1\n{config.digest}\n{seed}\n{mode}\n{trial_id}\n")
        scopes = {scope.scope_id: scope for scope in config.scopes}
        choices = []
        for rule in config.rules:
            for ordinal in range(rule.count):
                def draw(name, bound):
                    return _draw(sampling_key, rule.rule_id, ordinal, name, bound)
                scope = scopes[rule.scope_ids[draw("scope", len(rule.scope_ids))]]
                onset = rule.onset_min + draw("onset", rule.onset_max - rule.onset_min + 1)
                duration = rule.duration_min + draw("duration", rule.duration_max - rule.duration_min + 1)
                intended = rule.severity_min_ppm + draw("severity", rule.severity_max_ppm - rule.severity_min_ppm + 1)
                available = list(scope.targets)
                for index in range(rule.targets_per_event):
                    chosen = index + draw(f"target-{index}", len(available) - index)
                    available[index], available[chosen] = available[chosen], available[index]
                targets = tuple(sorted(available[:rule.targets_per_event]))
                target_digest = _hash("hearthbound:scenario-targets:v1\n" + scope.digest + "\n"
                                      + "".join(target.wire() + "\n" for target in targets))
                pair_id = _hash(f"hearthbound:scenario-pair:v1\n{sampling_key}\n{rule.rule_id}\n{ordinal}\n")
                effective = intended if mode == "treatment" else 0 if mode == "sham" else None
                event = None
                if mode != "no_event":
                    identity = _hash(f"hearthbound:scenario-event:v1\n{context}\n{rule.rule_id}\n{ordinal}\n"
                                     f"{scope.digest}\n{target_digest}\n{onset}\n{duration}\n{intended}\n")
                    event = Event(identity, rule.kind, onset, duration, effective / PPM)
                choices.append(Choice(rule.rule_id, ordinal, pair_id, rule.kind, scope, targets,
                                      target_digest, onset, duration, intended, effective, event))
        choices = tuple(choices)
        schedule = Schedule(choice.event for choice in choices if choice.event is not None)
        header = (f"hearthbound:scenario-manifest:v1\nGENERATOR\t{GENERATOR}\nSEED\t{seed}\nMODE\t{mode}\n"
                  f"TRIAL\t{trial_id}\nCONFIG_BYTES\t{len(config.canonical)}\n").encode("ascii")
        lines = [f"CONFIG_SHA256\t{config.digest}", f"CHOICES\t{len(choices)}"]
        for choice in choices:
            lines.append(f"CHOICE\t{choice.rule_id}\t{choice.ordinal}\t{choice.pair_id}\t{choice.kind}\t"
                         f"{choice.scope.scope_id}\t{choice.scope.digest}\t{choice.target_digest}\t{choice.onset}\t"
                         f"{choice.duration}\t{choice.intended_ppm}\t"
                         f"{choice.effective_ppm if choice.effective_ppm is not None else '-'}\t"
                         f"{choice.event.event_id if choice.event is not None else '-'}\t{len(choice.targets)}")
            lines.extend(f"TARGET\t{target.wire()}" for target in choice.targets)
        lines.extend([f"SCHEDULE_SHA256\t{schedule.digest}", f"EVENT_COUNT\t{len(schedule.events)}"])
        manifest = header + config.canonical + ("\n".join(lines) + "\n").encode("ascii")
        if len(manifest) > MAX_MANIFEST_BYTES:
            raise ValueError("manifest byte capacity exceeded")
        manifest_digest = _hash(manifest)
        journal_run_id = _hash(f"hearthbound:scenario-run:v1\n{manifest_digest}\n{trial_id}\n")
        values = locals()
        for name in ("config", "seed", "mode", "trial_id", "sampling_key", "choices", "schedule", "manifest",
                     "manifest_digest", "journal_run_id"):
            object.__setattr__(self, name, values[name])
        object.__setattr__(self, "_by_event", MappingProxyType({choice.event.event_id: choice for choice in choices
                                                              if choice.event is not None}))

    @classmethod
    def from_manifest(cls, data):
        _document(data, MAX_MANIFEST_BYTES)
        parts = data.split(b"\n", 6)
        if len(parts) != 7 or parts[0] != b"hearthbound:scenario-manifest:v1" or parts[1] != f"GENERATOR\t{GENERATOR}".encode("ascii"):
            raise ValueError("unsupported scenario manifest or generator version")
        values = []
        for line, tag in zip(parts[2:6], ("SEED", "MODE", "TRIAL", "CONFIG_BYTES")):
            fields = line.decode("ascii").split("\t")
            if len(fields) != 2 or fields[0] != tag:
                raise ValueError("invalid scenario manifest header")
            values.append(fields[1])
        length = _integer(_number(values[3]), 1, MAX_CONFIG_BYTES)
        config = Config.from_bytes(parts[6][:length])
        scenario = cls(config, _number(values[0]), values[1], values[2])
        if scenario.manifest != data:
            raise ValueError("manifest differs from the complete regenerated scenario")
        return scenario

    def event_choice(self, event_id):
        try:
            return self._by_event[event_id]
        except (KeyError, TypeError) as error:
            raise ValueError("unknown or foreign scenario event") from error

    def create_scheduler(self, path, world_id):
        return Scheduler.create(path, self.schedule, world_id, self.journal_run_id)

    def open_scheduler(self, path, world_id):
        return Scheduler.open(path, self.schedule, world_id, self.journal_run_id)
