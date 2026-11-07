#!/usr/bin/env python3
"""Real Minecraft restart attestation for causal mill receipts; no reward delivery.

Run only AFTER the first-phase Sable/Create test has saved the game and stopped.
The pre-restart JSON is an operator-only reference, never a citizen observation.
"""
import json
import os
import re
import socket
import struct
import uuid
from pathlib import Path

CHECKPOINT = Path("mill-outcome-pre-restart.json")
assert CHECKPOINT.is_file(), "Missing first-phase outcome reference"
before = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
assert before.get("schema") == "hearthbound.outcome-restart-checkpoint.v1"
job = str(uuid.UUID(before["job"]))
expected = before["receipt"]
assert "MILL_OUTCOME_PROPOSAL status=PROPOSED" in expected
assert "reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT" in expected

def packet(seq, kind, command):
    body=struct.pack("<ii",seq,kind)+command.encode()+b"\0\0"
    return struct.pack("<i",len(body))+body

def exact(sock,n):
    result=b""
    while len(result)<n:
        block=sock.recv(n-len(result))
        if not block:
            raise ConnectionError("RCON disconnected mid-frame")
        result+=block
    return result

def response(sock):
    size=struct.unpack("<i",exact(sock,4))[0]
    if not 10<=size<=1000000:
        raise ValueError("Bad RCON frame size")
    body=exact(sock,size)
    return struct.unpack("<i",body[:4])[0],body[8:-2].decode(errors="replace")

class Rcon:
    def __enter__(self):
        self.socket=socket.create_connection(("127.0.0.1",25575),timeout=20)
        self.socket.settimeout(20)
        self.socket.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        rid,_=response(self.socket)
        if rid!=1:
            rid,_=response(self.socket)
        if rid!=1:
            raise AssertionError("RCON authentication failed")
        self.id=10
        return self
    def __exit__(self,*_):
        self.socket.close()
    def run(self,cmd):
        self.id+=1
        self.socket.sendall(packet(self.id,2,cmd))
        rid,output=response(self.socket)
        if rid!=self.id:
            raise AssertionError(f"Wrong RCON response ID: {rid}")
        print(f"RESTART_OUTCOME_RCON {cmd} => {output}",flush=True)
        return output

with Rcon() as r:
    r.run("forceload add 0 0")
    presence=r.run("execute if entity @e[type=minecraft:villager,name=Sable]")
    if "Test passed" not in presence:
        raise AssertionError("Sable not loaded after server restart")
    raw=r.run(f"sable mill-process {job}")
    if "MILL_PROCESS VERIFIED_CALLBACK" not in raw or "NO_RESEARCH_CREDIT" not in raw:
        raise AssertionError("Actual Create callback not persisted: "+raw)
    lease=r.run("sable mill-reservation 7 101 1")
    if "MILL_RESERVATION HELD" not in lease or f"job={job}" not in lease:
        raise AssertionError("Previously held machine lease did not survive restart: "+lease)

    # Same physical actor, actual NBT, identical world UUID and time receipt.
    returned=r.run(f"execute positioned 7 101 1 run sable mill-outcome-probe {job}")
    if returned != expected:
        raise AssertionError("Causal outcome differs across true Forge save/restart:\n"
                             "before="+expected+"\nafter="+returned)
    print("REAL_FORGE_OUTCOME_RESTART_EXACT_MATCH",flush=True)

    duplicate=r.run(f"execute positioned 7 101 1 run sable mill-outcome-probe {job}")
    if duplicate != expected:
        raise AssertionError("Repeat post-restart inspection changed attribution")
    wrong=r.run("execute positioned 7 101 1 run sable mill-outcome-probe "
                "00000000-0000-4000-8000-000000000001")
    if "status=DENIED reason=NO_CREATE_CALLBACK" not in wrong:
        raise AssertionError("Unknown job attributed after restart: "+wrong)

    # Physical receipt remains historic truth; releasing the lease must revoke
    # proposal eligibility, even if the operator clears the output inventory.
    r.run("data modify block 7 101 1 OutputInventory.Items set value []")
    release=r.run(f"execute positioned 7 101 1 run sable mill-release 7 101 1 {job}")
    if "Mill reservation released with audit tombstone" not in release:
        raise AssertionError("Could not close original job after restart: "+release)
    denied=r.run(f"execute positioned 7 101 1 run sable mill-outcome-probe {job}")
    if "status=DENIED reason=TAINTED_OR_UNHELD_RESERVATION" not in denied:
        raise AssertionError("Released historic evidence was incorrectly credited: "+denied)
    surviving=r.run(f"sable mill-process {job}")
    if "MILL_PROCESS VERIFIED_CALLBACK" not in surviving or "NO_RESEARCH_CREDIT" not in surviving:
        raise AssertionError("Historical callback unexpectedly removed after release")
    print("REAL_FORGE_OUTCOME_RESTART_PASS receipt_exact=true "
          "duplicate_stable=true released_denied=true "
          "reward_authorized=false learning_authorized=false",flush=True)
