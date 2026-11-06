#!/usr/bin/env python3
"""Real Forge obstruction recovery: two physical villagers, one blocked route.

Only the disposable CI operator modifies blocks. Sable uses the unchanged
scripted server-side hauling code. No neural model can read these interventions.
"""
import os
import re
import socket
import time

from rcon_two_citizen_haul_acceptance import (
    Rcon, packet, exact, run_trial as baseline_trial, response, PASS,
    CITIZEN_A, CITIZEN_B, CHECK_DEST_A, CHECK_DEST_B
)

POLL_SECONDS=2
MAX_POLLS=75
SOURCE_A=11
DEST_A=7
SOURCE_B=24
DEST_B=19
BARRIER="fill 9 100 0 9 102 2 minecraft:stone"
OPEN_BARRIER="fill 9 100 0 9 102 2 minecraft:air"

def counts(rcon,source,destination,from_count,to_count):
    for x,n in ((source,from_count),(destination,to_count)):
        rcon.require(
            f'execute if data block {x} 100 1 Items[{{id:"minecraft:wheat",Count:{n}b}}]',
            PASS)

def inventory_empty(rcon,x):
    # Fresh Minecraft chest has no Items entries. Reject accidental insertions
    # rather than treating an absent expected item as an empty inventory.
    rcon.require(f'execute unless data block {x} 100 1 Items[0]',PASS)

def source_owned(rcon,x):
    result=rcon.run(f"hearthboundclaims owner {x} 100 1")
    if "belongs to" not in result:
        raise AssertionError(f"Source {x} claim lost or absent: {result}")

def source_unclaimed(rcon,x):
    rcon.require(f"hearthboundclaims owner {x} 100 1","No source claim")

def audit_cargo(rcon,locator,phase):
    output=rcon.require(locator+"sable haul-audit","AUDIT job=")
    if (f"phase={phase}" not in output or
        "cargo=1x" not in output or
        "claim=owned" not in output):
        raise AssertionError("Citizen lost confirmed cargo or claim: "+output)
    return output

def make_corridor(rcon):
    # Sealed hall (interior z=0..2, x=6..13): sides, ends, roof.
    # No alternate walking path around x=9 inside the fixture.
    rcon.require("forceload add 0 0 31 4","force loaded")
    rcon.require("fill 0 99 0 31 99 4 minecraft:stone","filled")
    rcon.run("fill 0 100 0 31 104 4 minecraft:air")
    for command in (
        "fill 5 100 0 5 103 2 minecraft:stone",
        "fill 14 100 0 14 103 2 minecraft:stone",
        "fill 5 100 -1 14 103 -1 minecraft:stone",
        "fill 5 100 3 14 103 3 minecraft:stone",
        "fill 5 103 0 14 103 2 minecraft:stone",
        BARRIER
    ):
        rcon.require(command,"filled")
    for chest in (SOURCE_A,DEST_A,SOURCE_B,DEST_B):
        rcon.require(f"setblock {chest} 100 1 minecraft:chest replace","changed the block")
    for chest in (SOURCE_A,SOURCE_B):
        rcon.require(
            f'data merge block {chest} 100 1 {{Items:[{{Slot:0b,id:"minecraft:wheat",Count:8b}}]}}',
            "modified")

def run_obstruction(rcon,sleep=time.sleep):
    make_corridor(rcon)
    # A begins INSIDE the sealed corridor, east of the barrier. The other
    # citizen is far outside. Source A at x11 and dest A at x7 remain
    # unreachable from one another until the operator removes the barrier.
    rcon.require("execute positioned 12 100 1 run sable spawn","Sable spawned")
    rcon.require(CITIZEN_B+"sable spawn","Sable spawned")
    rcon.require("execute if entity @e[type=minecraft:villager,name=Sable]","Test passed, count: 2")
    rcon.require("execute positioned 12 100 1 run sable haul 11 100 1 7 100 1",
                 "Sable assigned wheat haul")
    rcon.require(CITIZEN_B+"sable haul 24 100 1 19 100 1",
                 "Sable assigned wheat haul")
    rcon.require("hearthboundclaims count","Active source claims in this dimension: 2")
    source_owned(rcon,SOURCE_A)
    source_owned(rcon,SOURCE_B)

    # Require direct evidence that A actually extracted a single wheat item
    # and retained the reservation, rather than simply staying at the source.
    carrying=False
    b_delivered=False
    for i in range(MAX_POLLS):
        sleep(POLL_SECONDS)
        observed=rcon.require("execute positioned 12 100 1 run sable haul-audit","AUDIT job=")
        if "phase=1" in observed and "cargo=1x" in observed:
            carrying=True
        if not b_delivered:
            b_delivered=PASS in rcon.run(CHECK_DEST_B).lower()
        if carrying and b_delivered:break
        if i in (14,29,44,59):
            print("OBSTRUCTED_HAUL_PREOPEN_POLL index="+str(i+1)
                  +" carrying="+str(carrying).lower()
                  +" b_delivered="+str(b_delivered).lower()
                  +" A="+observed,flush=True)
    if not carrying or not b_delivered:
        raise AssertionError("Blocked A failed to acquire cargo or independent B failed to deliver")
    # At least 20 extra world ticks under obstruction; no agent/world-state
    # mutation except the scripted simulation running on the Forge server.
    sleep(2)
    audit_cargo(rcon,"execute positioned 12 100 1 run ",1)
    counts(rcon,SOURCE_A,DEST_A,7,0) if False else None
    counts(rcon,SOURCE_A,SOURCE_A,7,7)
    inventory_empty(rcon,DEST_A)
    counts(rcon,SOURCE_B,DEST_B,7,1)
    source_owned(rcon,SOURCE_A)
    source_unclaimed(rcon,SOURCE_B)
    rcon.require("hearthboundclaims count","Active source claims in this dimension: 1")
    # Check physical obstacle remains solid before claiming a causal effect.
    rcon.require("execute if block 9 100 1 minecraft:stone",PASS)
    print("OBSTRUCTED_HAUL_HOLD_CONFIRMED A_cargo=1 "
          "A_destination_empty=true A_claim_owned=true "
          "B_delivered=true B_claim_released=true",flush=True)

    rcon.require(OPEN_BARRIER,"filled")
    rcon.require("execute if block 9 100 1 minecraft:air",PASS)
    recovered=False
    for i in range(MAX_POLLS):
        sleep(POLL_SECONDS)
        if PASS in rcon.run(CHECK_DEST_A).lower():
            recovered=True
            print("OBSTRUCTED_HAUL_RECOVERED poll="+str(i+1),flush=True)
            break
        if i in (14,29,44,59):
            print("OBSTRUCTED_HAUL_POSTOPEN_POLL index="+str(i+1)
                  +" A="+rcon.run("execute positioned 12 100 1 run sable haul-audit"),
                  flush=True)
    if not recovered:raise AssertionError("A did not physically deliver after removing barrier")
    counts(rcon,SOURCE_A,DEST_A,7,1)
    counts(rcon,SOURCE_B,DEST_B,7,1)
    source_unclaimed(rcon,SOURCE_A)
    source_unclaimed(rcon,SOURCE_B)
    rcon.require("hearthboundclaims count","Active source claims in this dimension: 0")
    rcon.require("execute positioned 7.5 100 1.5 if entity "
                 "@e[type=minecraft:villager,name=Sable,distance=..2.6]",PASS)
    rcon.require("execute positioned 19.5 100 1.5 if entity "
                 "@e[type=minecraft:villager,name=Sable,distance=..2.6]",PASS)
    print("REAL_FORGE_OBSTRUCTED_HAUL_PASS two_real_villagers=true "
          "A_held_cargo_during_barrier=true B_completed_while_A_blocked=true "
          "A_recovered_after_unblock=true source_wheat=7,7 destination_wheat=1,1 "
          "claims_outstanding=0 neural_training=false",flush=True)

def main():
    with socket.create_connection(("127.0.0.1",25575),timeout=15) as sock:
        sock.settimeout(20)
        sock.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        for _ in range(4):
            n=int.from_bytes(exact(sock,4),"little",signed=True)
            if not 10<=n<=1000000:raise ValueError("invalid auth frame")
            frame=exact(sock,n)
            if int.from_bytes(frame[:4],"little",signed=True)==1:break
        else:raise AssertionError("RCON auth failed")
        run_obstruction(Rcon(sock))

if __name__=="__main__":
    main()
