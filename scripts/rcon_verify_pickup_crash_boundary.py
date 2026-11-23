#!/usr/bin/env python3
"""Verify world/journal divergence after externally killed actual Forge JVM.

The original fixture is saved BEFORE dispatch; the motor's later extraction
takes place with saves off. Never infer cargo from journal or reward an agent.
"""
import json
import math
import os
import re
import time
from pathlib import Path
from uuid import UUID
from rcon_neural_report_haul import Rcon

A, B, D = "3 101 1", "7 101 1", "10 101 2"
HAUL_PATH = 'ForgeData."hearthbound.haul"'
UUID_TEXT = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

def value(receipt, field):
    m = re.search(r"\b" + field + r"=([^\s]+)", receipt)
    if not m:
        raise AssertionError(f"Missing {field}: {receipt}")
    return m.group(1)


def strict_uuid(value, label):
    """Accept a canonical identity, never a selector or alternate UUID syntax."""
    if not isinstance(value, str) or not UUID_TEXT.fullmatch(value):
        raise AssertionError(f"Invalid {label} UUID: {value!r}")
    if str(UUID(value)) != value:
        raise AssertionError(f"Noncanonical {label} UUID: {value!r}")
    return value


def executor_from_receipt(receipt, label):
    if not isinstance(receipt, str):
        raise AssertionError(f"Missing {label} receipt")
    identities = re.findall(r"(?:^|\s)executor=([^\s]+)", receipt)
    if len(identities) != 1:
        raise AssertionError(f"Expected one executor in {label} receipt")
    return strict_uuid(identities[0], label + " executor")


def original_executor(checkpoint, durable_receipt):
    """Bind restart inspection to the original dispatched and journaled actor."""
    if not isinstance(checkpoint, dict):
        raise AssertionError("Missing original dispatch checkpoint")
    expected = executor_from_receipt(checkpoint.get("dispatch"), "original dispatch")
    actual = executor_from_receipt(durable_receipt, "durable job")
    if actual != expected:
        raise AssertionError("Durable executor differs from original dispatch executor")
    return expected


def wait_for_original_executor(rcon, executor, *, timeout=10.0, poll_interval=0.1,
                               clock=time.monotonic, sleep=time.sleep):
    """Read-only readiness; absent actors are never repaired or accepted.

    ``timeout`` is the acceptance deadline. Late responses cannot pass; a
    blocked query retains the existing RCON transport timeout and may take
    longer to fail. This helper does not change shared transport behavior.
    """
    executor = strict_uuid(executor, "original executor")
    if (not math.isfinite(timeout) or not math.isfinite(poll_interval)
            or timeout <= 0 or poll_interval <= 0):
        raise ValueError("Executor readiness requires finite positive time bounds")
    started = clock()
    deadline = started + timeout
    attempts = 0
    last_response = "not queried"
    # The attempt cap also bounds queries if an injected clock fails to advance.
    maximum_attempts = math.ceil(timeout / poll_interval) + 1
    while clock() < deadline and attempts < maximum_attempts:
        response = rcon.run(f"execute if entity {executor}")
        attempts += 1
        now = clock()
        last_response = response.strip()
        if last_response == "Test passed, count: 1" and now <= deadline:
            return {"executor": executor, "attempts": attempts,
                    "wait_seconds": max(0.0, now - started),
                    "timeout_seconds": timeout}
        if last_response not in ("Test failed", "No entity was found",
                                  "Test passed, count: 1"):
            raise AssertionError("Unexpected original-executor readiness response: "
                                 + response)
        remaining = deadline - now
        if remaining <= 0:
            break
        sleep(min(poll_interval, remaining))
    raise AssertionError("MISSING_BASELINE_EXECUTOR executor=" + executor
                         + " timeout_seconds=" + str(timeout)
                         + " attempts=" + str(attempts)
                         + " last_response=" + repr(last_response))


def verify_unsaved_haul_absent(rcon, executor):
    """A missing entity is different from an absent field on that exact entity."""
    executor = strict_uuid(executor, "original executor")
    response = rcon.run(f"data get entity {executor} {HAUL_PATH}")
    if response.strip() == "No entity was found":
        raise AssertionError("MISSING_BASELINE_EXECUTOR executor=" + executor
                             + " during_unsaved_haul_inspection")
    if response.strip() != "Found no elements matching " + HAUL_PATH:
        raise AssertionError("Unsaved assignment unexpectedly exists or could not "
                             "be verified: " + response)
    return response


def main():
    boundary = os.environ["HEARTHBOUND_CRASH_BOUNDARY"]
    insertion_boundaries = {"AFTER_DELIVERY_INTENT", "AFTER_INSERTION",
                            "AFTER_DELIVERY_RETURN"}
    expected = ("CARGO_RETURNED" if boundary == "AFTER_OUTCOME"
                or boundary in insertion_boundaries else "UNRESOLVED")
    delivery_expected = ("INSERTION_RETURNED" if boundary == "AFTER_DELIVERY_RETURN"
                         else "INSERTION_UNRESOLVED" if boundary in insertion_boundaries
                         else "NOT_STARTED")
    checkpoint = json.loads(Path("pickup-crash-arm.json").read_text())
    marker = Path("run/pickup-crash-boundary.marker").read_text().strip()
    if not marker.startswith("HEARTHBOUND_PICKUP_BOUNDARY " + boundary + " job=" + checkpoint["job"]):
        raise AssertionError("Wrong forced marker: " + marker)
    # Main world chunks and citizen records are from the saved baseline.
    # No actual motor action may be replayed from a journal observation.
    with Rcon() as r:
        audit = r.require("hearthbound-pickup-journal", "status=READ_ONLY")
        if (value(audit, "total") != "1"
            or value(audit, "extraction_empty") != "0"
            or value(audit, "unresolved") != ("0" if expected == "CARGO_RETURNED" else "1")
            or value(audit, "cargo_returned") != ("1" if expected == "CARGO_RETURNED" else "0")):
            raise AssertionError("Journal replay at crash boundary invalid: " + audit)
        specific = r.require(
            "hearthbound-pickup-job " + checkpoint["job"], "status=READ_ONLY")
        if (value(specific, "job") != checkpoint["job"]
                or value(specific, "state") != expected
                or value(specific, "delivery_state") != delivery_expected
                or value(specific, "source") != "minecraft:overworld|3,101,1"
                or value(specific, "task_authorized") != "false"
                or value(specific, "reward_authorized") != "false"):
            raise AssertionError("Journal record does not match killed physical job: "
                                 + specific)
        expected_destination = ("minecraft:overworld|10,101,2"
                                if boundary in insertion_boundaries else "NONE")
        if value(specific, "delivery_destination") != expected_destination:
            raise AssertionError("Persisted delivery destination mismatch: " + specific)
        recorded_delivery_tick = int(value(specific, "delivery_tick"))
        if ((boundary in insertion_boundaries and recorded_delivery_tick < 0)
                or (boundary not in insertion_boundaries and recorded_delivery_tick != -1)):
            raise AssertionError("Delivery tick is inconsistent with crash point: " + specific)
        marker_world = value(marker, "world")
        if value(specific, "world") != marker_world:
            raise AssertionError("World UUID differs from forced boundary marker")
        executor = original_executor(checkpoint, specific)
        r.require(f"data get block {A} Items", "Count: 3b")
        r.require(f"data get block {B} Items", "Count: 1b")
        r.require(f"data get block {D} Items", "block data: []")
        # Server readiness does not establish that this saved entity is visible.
        # Poll only the original UUID; never spawn, move, load chunks or retry work.
        readiness = wait_for_original_executor(r, executor)
        print("HEARTHBOUND_PICKUP_EXECUTOR_READY "
              + json.dumps(readiness, sort_keys=True), flush=True)
        # Saving before dispatch deliberately excludes the later physical job.
        verify_unsaved_haul_absent(r, executor)
        r.require("save-all flush", "Saved the game")
        r.run("stop")
    Path("pickup-crash-verified.json").write_text(
        json.dumps({"schema": "hearthbound.real-pickup-crash-gate.v1",
                    "boundary": boundary, "job": checkpoint["job"],
                    "executor": executor, "executor_readiness": readiness,
                    "journal": audit, "job_receipt": specific,
                    "delivery_expected": delivery_expected, "inventory_baseline": {"A": 3, "B": 1, "dest": 0},
                    "unsaved_executor_job_restored": False,
                    "automatic_pickup_retry": False,
                    "physical_delivery_claimed": False,
                    "rewards_authorized": False}, indent=2) + "\n")
    print("HEARTHBOUND_PICKUP_CRASH_ACCEPTED boundary=" + boundary, flush=True)

if __name__ == "__main__":
    main()
