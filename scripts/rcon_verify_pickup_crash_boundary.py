#!/usr/bin/env python3
"""Verify world/journal divergence after externally killed actual Forge JVM.

The original fixture is saved BEFORE dispatch; the motor's later extraction
takes place with saves off. Never infer cargo from journal or reward an agent.
"""
import json
import os
import re
from pathlib import Path
from rcon_neural_report_haul import Rcon

A, B, D = "3 101 1", "7 101 1", "10 101 2"
EXECUTOR = "@e[type=minecraft:villager,name=Sable,limit=1]"

def value(receipt, field):
    m = re.search(r"\b" + field + r"=([^\s]+)", receipt)
    if not m:
        raise AssertionError(f"Missing {field}: {receipt}")
    return m.group(1)

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
        r.require(f"data get block {A} Items", "Count: 3b")
        r.require(f"data get block {B} Items", "Count: 1b")
        r.require(f"data get block {D} Items", "block data: []")
        # Saving before dispatch deliberately excludes the later physical job.
        no_haul = r.run(f'data get entity {EXECUTOR} ForgeData."hearthbound.haul"')
        if "Found no elements" not in no_haul:
            raise AssertionError("Unsaved assignment unexpectedly exists: " + no_haul)
        r.require("save-all flush", "Saved the game")
        r.run("stop")
    Path("pickup-crash-verified.json").write_text(
        json.dumps({"schema": "hearthbound.real-pickup-crash-gate.v1",
                    "boundary": boundary, "job": checkpoint["job"],
                    "journal": audit, "job_receipt": specific,
                    "delivery_expected": delivery_expected, "inventory_baseline": {"A": 3, "B": 1, "dest": 0},
                    "unsaved_executor_job_restored": False,
                    "automatic_pickup_retry": False,
                    "physical_delivery_claimed": False,
                    "rewards_authorized": False}, indent=2) + "\n")
    print("HEARTHBOUND_PICKUP_CRASH_ACCEPTED boundary=" + boundary, flush=True)

if __name__ == "__main__":
    main()
