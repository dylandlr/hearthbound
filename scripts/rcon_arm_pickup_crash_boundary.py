#!/usr/bin/env python3
"""Arm one actual report-policy pickup in disposable Forge crash-boundary CI.

Only creates test-world inventories and a valid physical scout report. It does
not kill the JVM, inspect journal files, grant credit or invent motor receipts.
"""
import json
import re
import time
from pathlib import Path

from rcon_neural_report_haul import Rcon

EXECUTOR = "@e[type=minecraft:villager,name=Sable,limit=1]"
SCOUT = "@e[type=minecraft:villager,tag=hb_crash_scout,limit=1]"
A, B, DEST = "3 101 1", "7 101 1", "10 101 2"

def main():
    expected_model = Path("run/report-choice-mlp-v1.sha256").read_text().strip()
    assert re.fullmatch(r"[0-9a-f]{64}", expected_model)
    with Rcon() as r:
        for cmd in (
            "gamerule doMobSpawning false",
            "forceload add 0 0",
            "fill 0 99 0 12 105 4 minecraft:air",
            "fill 0 100 0 12 100 4 minecraft:stone",
            'setblock 3 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]} replace',
            'setblock 7 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]} replace',
            "setblock 10 101 2 minecraft:chest replace",
        ):
            r.run(cmd)
        r.require("execute positioned 2 101 2 run sable spawn", "Sable spawned")
        for _ in range(60):
            if "Test passed" in r.run(f"execute if entity {EXECUTOR}"):
                break
            time.sleep(.1)
        else:
            raise AssertionError("No real executor")
        r.require(f"tp {EXECUTOR} 2 101 2", "Teleported")
        r.require(
            """summon minecraft:villager 4 101 3 {CustomName:'{"text":"CrashScout"}',Tags:["hb_crash_scout"],ForgeData:{"hearthbound.citizen":1b},NoAI:1b}""",
            "Summoned new",
        )
        for _ in range(60):
            if "Test passed" in r.run(f"execute if entity {SCOUT}"):
                break
            time.sleep(.1)
        else:
            raise AssertionError("No real scout")
        r.require(f"hearthbound citizen_observe {A} {SCOUT}", "wheat=3")
        r.require(f"hearthbound citizen_observe {B} {SCOUT}", "wheat=1")
        r.require(f"hearthbound-share-direct {A} {SCOUT} {EXECUTOR}", "status=DELIVERED")
        r.require(f"hearthbound-share-direct {B} {SCOUT} {EXECUTOR}", "status=DELIVERED")
        # Physical chest reads are EXTERNAL assertions only, never policy features.
        r.require(f"data get block {A} Items", "Count: 3b")
        r.require(f"data get block {B} Items", "Count: 1b")
        r.require(f"data get block {DEST} Items", "block data: []")
        # Commit world, scout reports and chest baseline BEFORE creating the
        # experimental job. Then suppress further saves so an actual JVM kill
        # can expose the journal-vs-NBT/world rollback boundary.
        r.require("save-all flush", "Saved the game")
        r.require("save-off", "Automatic saving is now disabled")
        selected = r.require(
            f"hearthbound-report-dispatch-trial {EXECUTOR} {A} {B} {DEST} SCRIPTED exposed",
            "status=ASSIGNED",
        )
        if "source=minecraft:overworld|3,101,1" not in selected:
            raise AssertionError("Unexpected policy choice: " + selected)
        m = re.search(r"\bjob=([0-9a-f-]{36})", selected)
        if not m:
            raise AssertionError("Missing physical job UUID")
        Path("pickup-crash-arm.json").write_text(
            json.dumps({"job": m.group(1), "dispatch": selected,
                        "world_fixture": "pickup-crash-boundary-world",
                        "A_initial": 3, "B_initial": 1,
                        "destination_initial": 0}, indent=2) + "\n"
        )
        print("HEARTHBOUND_PICKUP_CRASH_ARMED job=" + m.group(1), flush=True)

if __name__ == "__main__":
    main()
