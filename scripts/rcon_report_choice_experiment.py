#!/usr/bin/env python3
"""Paired real-Forge report visibility experiment. OPERATOR fixture only.

The POLICY is a deterministic scripted baseline over the recipient's already
delivered report NBT; it NEVER reads the live chest or executes a haul.
Physical chest reads here are operator-only oracle checks, outside the policy.
"""
import json
import os
import socket
import struct
import time
from pathlib import Path

def packet(seq,kind,command):
    body=struct.pack("<ii",seq,kind)+command.encode()+b"\0\0"
    return struct.pack("<i",len(body))+body

def exact(sock,n):
    out=b""
    while len(out)<n:
        fragment=sock.recv(n-len(out))
        if not fragment: raise ConnectionError("Minecraft RCON disconnected")
        out+=fragment
    return out

def response(sock):
    n=struct.unpack("<i",exact(sock,4))[0]
    if n < 10 or n > 1000000: raise ValueError("Invalid RCON frame length")
    body=exact(sock,n)
    return struct.unpack("<i",body[:4])[0],body[8:-2].decode(errors="replace")

class Rcon:
    def __enter__(self):
        self.sock=socket.create_connection(("127.0.0.1",25575),timeout=20)
        self.sock.settimeout(20)
        self.sock.sendall(packet(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        request_id,_=response(self.sock)
        if request_id != 1:
            request_id,_=response(self.sock)
        if request_id != 1: raise AssertionError("RCON authentication rejected")
        self.seq=10
        return self
    def __exit__(self,*_):
        self.sock.close()
    def run(self,cmd):
        self.seq+=1
        self.sock.sendall(packet(self.seq,2,cmd))
        rid,out=response(self.sock)
        if rid!=self.seq: raise AssertionError("RCON ID changed")
        print("REPORT_CHOICE_RCON",cmd,"=>",out,flush=True)
        return out
    def require(self,cmd,expected):
        out=self.run(cmd)
        if expected not in out:
            raise AssertionError(f"Expected {expected!r} from {cmd!r}, got {out!r}")
        return out

def checks(result):
    for marker in ("schema=hearthbound.report-choice.v1",
                   "policy=SCRIPTED_REPORT_RANK_V1",
                   "candidate_sources=minecraft:overworld|3,101,1;minecraft:overworld|7,101,1",
                   "evidence_origin=RECIPIENT_DELIVERED_REPORT_ONLY",
                   "inventory_read=false sensor_triggered=false",
                   "task_authorized=false reward_authorized=false",
                   "learning_authorized=false NO_RESEARCH_CREDIT"):
        if marker not in result: raise AssertionError("Unsafe report decision: "+result)
    return result

def run():
    receiver="@e[type=minecraft:villager,tag=hb_decision_receiver,limit=1]"
    sable="@e[type=minecraft:villager,name=Sable,limit=1]"
    prefix=f"hearthbound-report-choice {receiver} 3 101 1 7 101 1"
    facts={}
    with Rcon() as r:
        for cmd in (
            "gamerule doMobSpawning false",
            "forceload add 0 0",
            "fill 0 99 0 12 105 5 minecraft:air",
            "fill 0 100 0 12 100 5 minecraft:stone",
            'setblock 3 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]} replace',
            'setblock 7 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]} replace',
        ): r.run(cmd)
        r.require("execute positioned 2 101 2 run sable spawn","Sable spawned")
        r.require(f"tp {sable} 4 101 2","Teleported")
        summoned=r.run("""summon minecraft:villager 6 101 2 {CustomName:'{"text":"ReportRecipient"}',Tags:["hb_decision_receiver"],ForgeData:{"hearthbound.citizen":1b},NoAI:1b}""")
        if "Summoned new" not in summoned: raise AssertionError("Real recipient not summoned: "+summoned)
        r.require(f"execute if entity {receiver}","Test passed")

        # Before delivery, neither exposed nor withheld condition may find a
        # private report. No real inventory is read by this decision function.
        empty=checks(r.require(prefix+" exposed","status=ABSTAIN"))
        if "reason=NO_FRESH_ADMISSIBLE_REPORT" not in empty:
            raise AssertionError("Recipient acquired reports before communication")
        withheld0=checks(r.require(prefix+" withheld","status=ABSTAIN"))
        if "reason=REPORT_EXPOSURE_WITHHELD" not in withheld0:
            raise AssertionError("Blind arm did not abstain before communication")

        # True physical memory is created on the sender, not the receiver.
        r.require(f"hearthbound citizen_observe 3 101 1 {sable}","wheat=3")
        r.require(f"hearthbound citizen_observe 7 101 1 {sable}","wheat=1")
        r.require(f"hearthbound knowledge_share 3 101 1 {receiver}","status=DELIVERED")
        r.require(f"hearthbound knowledge_share 7 101 1 {receiver}","status=DELIVERED")
        before_a=r.require("data get block 3 101 1 Items",'Count: 3b')
        before_b=r.require("data get block 7 101 1 Items",'Count: 1b')
        # Same physical world and exactly the same candidate menu; the only
        # manipulated value is access to the recipient's delivered reports.
        arm_withheld=checks(r.require(prefix+" withheld","status=ABSTAIN"))
        arm_exposed=checks(r.require(prefix+" exposed","status=CHOOSE"))
        if "selected=minecraft:overworld|3,101,1" not in arm_exposed:
            raise AssertionError("Information-exposed policy ignored higher reported wheat")
        if "selected=NONE" not in arm_withheld:
            raise AssertionError("Withheld policy leaked private report")
        after_a=r.require("data get block 3 101 1 Items",'Count: 3b')
        after_b=r.require("data get block 7 101 1 Items",'Count: 1b')
        if before_a!=after_a or before_b!=after_b:
            raise AssertionError("Decision experiment mutated world inventory")
        print("REAL_FORGE_REPORT_EXPOSURE_PAIRED_PASS same_world=true same_menu=true "
              "withheld=ABSTAIN exposed=SOURCE_A inventory_unchanged=true",flush=True)

        # Intervene ONLY on physical inventory. Neither report nor policy
        # changes yet; policy must reveal its stale limited knowledge rather
        # than silently inspect the new source state.
        r.require('data modify block 3 101 1 Items set value []',"Modified block data")
        stale=checks(r.require(prefix+" exposed","status=CHOOSE"))
        if "selected=minecraft:overworld|3,101,1" not in stale:
            raise AssertionError("Policy learned operator chest mutation without communication")
        # A new direct EMPTY observation is shared. This must supersede the
        # previous AVAILABLE(3) report, even within the SAME server tick.
        r.require(f"hearthbound citizen_observe 3 101 1 {sable}","wheat=0")
        r.require(f"hearthbound knowledge_share 3 101 1 {receiver}","status=DELIVERED")
        revised=checks(r.require(prefix+" exposed","status=CHOOSE"))
        if "selected=minecraft:overworld|7,101,1" not in revised:
            raise AssertionError("New EMPTY report did not invalidate old A source: "+revised)
        if "selected=NONE" not in checks(r.require(prefix+" withheld","status=ABSTAIN")):
            raise AssertionError("Withheld arm learned from other experiment condition")
        r.require("data get block 3 101 1 Items","has the following block data: []")
        r.require("data get block 7 101 1 Items","Count: 1b")
        facts={
            "schema":"hearthbound.forge-paired-report-exposure.v1",
            "origin":"REAL_FORGE_RCON",
            "policy":"SCRIPTED_REPORT_RANK_V1",
            "same_world":True,"same_candidate_menu":True,
            "world_inventory_held_constant_during_paired_test":True,
            "before_report_status":"ABSTAIN",
            "withheld_after_report":"ABSTAIN",
            "exposed_after_report":"CHOOSE_SOURCE_A",
            "after_unannounced_source_mutation":"CHOOSE_SOURCE_A_STALE",
            "after_new_empty_report":"CHOOSE_SOURCE_B",
            "physical_haul_executed":False,"reward_authorized":False,
            "neural_learning_performed":False,"research_credit":0,
        }
        Path("real-report-choice-results.json").write_text(
            json.dumps(facts,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print("REAL_FORGE_REPORT_UPDATE_SWITCH_PASS old_report_superseded=true "
              "no_omniscient_inventory_read=true no_task_or_reward=true",flush=True)

if __name__=="__main__":
    run()
