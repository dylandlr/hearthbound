#!/usr/bin/env python3
"""Real Minecraft partial-world rollback fault injection.

Modes:
  seed:  establish the SAME persisted world UUID, but no Create process receipt.
  verify: run after CI deliberately replaces the Create SavedData with an older
          (absent) snapshot while leaving the world ID, citizen, and separate
          fsynced causal audit journal intact.

This is strictly an operator acceptance test, never an agent action or payout.
"""
import json
import os
import socket
import struct
import sys
import time
import uuid
from pathlib import Path

MISSING_JOB = "00000000-0000-4000-8000-000000000001"

def packet(request_id, kind, text):
    body = struct.pack("<ii", request_id, kind) + text.encode() + b"\x00\x00"
    return struct.pack("<i",len(body)) + body

def exact(sock, size):
    out=b""
    while len(out)<size:
        data=sock.recv(size-len(out))
        if not data:
            raise ConnectionError("RCON disconnected")
        out+=data
    return out

def answer(sock):
    n=struct.unpack("<i",exact(sock,4))[0]
    if n<10 or n>1000000:
        raise ValueError("Invalid RCON packet")
    payload=exact(sock,n)
    return struct.unpack("<i",payload[:4])[0],payload[8:-2].decode(errors="replace")

class Rcon:
    def __enter__(self):
        self.sock=socket.create_connection(("127.0.0.1",25575),timeout=20)
        self.sock.settimeout(20)
        self.sock.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        rid,_=answer(self.sock)
        if rid!=1:
            rid,_=answer(self.sock)
        if rid!=1:
            raise RuntimeError("RCON login rejected")
        self.seq=10
        return self
    def __exit__(self,*args):
        self.sock.close()
    def run(self,command):
        self.seq+=1
        self.sock.sendall(packet(self.seq,2,command))
        rid,result=answer(self.sock)
        if rid!=self.seq:
            raise RuntimeError("RCON sequence mismatch")
        print(f"ROLLBACK_RCON {command} => {result}",flush=True)
        return result
    def require(self,command,needle):
        result=self.run(command)
        if needle not in result:
            raise AssertionError(f"Expected {needle!r} in {command!r}: {result}")
        return result

def seed():
    with Rcon() as r:
        r.run("forceload add 0 0")
        r.run("setblock 2 100 1 minecraft:stone replace")
        r.require("execute positioned 2 101 1 run sable spawn","Sable spawned")
        empty=r.run("execute positioned 2 101 1 run sable mill-outcome-journal "+MISSING_JOB)
        if "state=DENIED reason=UNVERIFIED_MINECRAFT_EVIDENCE" not in empty:
            raise AssertionError("Could not initialize world-bound empty causal journal: "+empty)
        killed=r.run("kill @e[type=minecraft:villager,name=Sable]")
        if "Killed" not in killed:
            raise AssertionError("Could not clear initial operator fixture villager: "+killed)
        # Entity death/removal is tick-delayed; saving immediately after /kill
        # can persist a dying marked villager that contaminates the next boot's
        # unqualified @e[name=Sable,limit=1] selector.
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            empty=r.run("execute unless entity @e[type=minecraft:villager,name=Sable]")
            if "Test passed" in empty: break
            time.sleep(0.5)
        else:
            raise AssertionError("Killed baseline Sable remained selectable before save: "+empty)
        r.require("save-all flush","Saved the game")
        r.run("stop")
        print("ROLLBACK_BASELINE_SAVED_WITH_WORLD_ID_AND_NO_PROCESS",flush=True)

def verify():
    baseline=json.loads(Path("mill-outcome-pre-restart.json").read_text(encoding="utf-8"))
    if baseline.get("schema") != "hearthbound.outcome-restart-checkpoint.v1":
        raise AssertionError("Incorrect pre-rollback fixture")
    job=str(uuid.UUID(baseline["job"]))
    admitted=baseline["journal"]
    if ("CAUSAL_EVIDENCE_JOURNAL state=ADMITTED revalidated=true" not in admitted
            or "reward_authorized=false learning_authorized=false" not in admitted):
        raise AssertionError("No original admitted, audit-only evidence to roll back")
    with Rcon() as r:
        r.run("forceload add 0 0")
        r.require("execute if entity @e[type=minecraft:villager,name=Sable]","Test passed")
        process=r.run(f"sable mill-process {job}")
        # This command intentionally reports TAINTED before reading the raw
        # callback map. A resumed mill can legitimately be marked tainted
        # after the old data was removed. Neither NONE nor INVALIDATED may
        # be mistaken for a verified callback; the outcome probe below
        # independently proves the saved raw callback is absent.
        if not ("MILL_PROCESS NONE" in process or
                "MILL_PROCESS INVALIDATED" in process):
            raise AssertionError("Unexpected Create audit result after rollback: "+process)
        if "MILL_PROCESS VERIFIED_CALLBACK" in process:
            raise AssertionError("Rolled-back Create callback still verified: "+process)
        # A world UUID and a still-present villager alone can never substitute
        # for the physical Create callback that was deliberately rolled back.
        invalid=r.run(f"execute positioned 7 101 1 run sable mill-outcome-probe {job}")
        if "status=DENIED reason=NO_CREATE_CALLBACK" not in invalid:
            raise AssertionError("Rolled-back Create process still got proposed: "+invalid)
        audit=r.run(f"execute positioned 7 101 1 run sable mill-outcome-journal {job}")
        for marker in ("CAUSAL_EVIDENCE_JOURNAL state=REVOKED",
                       "revalidated=false","reward_authorized=false",
                       "learning_authorized=false","NO_RESEARCH_CREDIT"):
            if marker not in audit:
                raise AssertionError("Old journal was trusted after rollback: "+audit)
        if audit == admitted:
            raise AssertionError("Past ADMITTED state was accepted without the source")
        repeat=r.run(f"execute positioned 7 101 1 run sable mill-outcome-journal {job}")
        if repeat != audit:
            raise AssertionError("Replayed revoked event lost terminal state")
        r.require("save-all flush","Saved the game")
        print("REAL_FORGE_CAUSAL_ROLLBACK_REVOKED actual_callback_missing=true "
              "journal_remained=true world_uuid_unchanged=true "
              "no_research_credit=true no_model_updates=true",flush=True)

if __name__=="__main__":
    if len(sys.argv)!=2 or sys.argv[1] not in ("seed","verify"):
        raise SystemExit("Usage: rcon_causal_rollback.py seed|verify")
    (seed if sys.argv[1]=="seed" else verify)()
