#!/usr/bin/env python3
"""Pin restart probes to the physical executor, independent of nearby names."""
from dataclasses import dataclass
import math
import re
import time
from uuid import UUID


def _uuid(value):
    if not isinstance(value, str) or str(UUID(value)) != value:
        raise ValueError("Noncanonical restart identity")
    return value


def _field(text, name):
    matches = re.findall(r"(?:^|\s)" + re.escape(name) + r"=([^\s]+)", text)
    if len(matches) != 1:
        raise ValueError("Missing or ambiguous restart field: " + name)
    return matches[0]


@dataclass(frozen=True)
class RestartIdentity:
    job: str
    citizen: str
    world: str


def checkpoint_identity(checkpoint):
    """All three pre-restart witnesses must identify the same original job."""
    if checkpoint.get("schema") != "hearthbound.outcome-restart-checkpoint.v1":
        raise ValueError("Unknown restart checkpoint schema")
    receipt, journal, learning = (checkpoint[name] for name in ("receipt", "journal", "learning"))
    identity = RestartIdentity(_uuid(checkpoint["job"]), _uuid(_field(receipt, "citizen")),
                               _uuid(_field(receipt, "world")))
    physical = _field(receipt, "physical_evidence_id")
    event = "hearthbound:mill:v1:" + identity.world + ":minecraft:overworld:" + identity.job
    if (_field(receipt, "job") != identity.job
            or _field(journal, "job") != identity.job
            or _field(journal, "citizen") != identity.citizen
            or _field(journal, "world") != identity.world
            or _field(journal, "physical_evidence") != physical
            or _field(journal, "event") != event
            or _field(learning, "citizen") != identity.citizen
            or _field(learning, "physical_evidence_id") != physical
            or _field(learning, "event") != event):
        raise ValueError("Pre-restart witnesses disagree on original executor/job/world/evidence")
    return identity


def executor_command(citizen, command):
    """Use the original entity's current location, never a nearest-name anchor."""
    _uuid(citizen)
    if not command.startswith("sable ") or "\n" in command or "\r" in command:
        raise ValueError("Expected one actor-scoped Sable command")
    return f"execute as {citizen} at @s run {command}"


def wait_for_executor(rcon, citizen, timeout=30, clock=time.monotonic, sleep=time.sleep):
    """Bounded read-only readiness; never creates, replaces, moves or freezes actors."""
    _uuid(citizen)
    if not math.isfinite(timeout) or timeout <= 0 or timeout > 60:
        raise ValueError("Readiness timeout must be positive and at most 60 seconds")
    deadline = clock() + timeout
    last = "not queried"
    while clock() < deadline:
        last = rcon.run(f"execute if entity {citizen}").strip()
        if last == "Test passed, count: 1" and clock() < deadline:
            return
        remaining = deadline - clock()
        if remaining > 0:
            sleep(min(0.25, remaining))
    raise AssertionError("Original outcome executor did not load within readiness window: " + last)
