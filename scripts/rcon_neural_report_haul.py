#!/usr/bin/env python3
"""Actual Minecraft physical neural dispatch acceptance, not shadow inference.

Two real citizens: a marked scout directly observes two real wheat chests,
explicitly communicates those observations to Sable, and Sable's own frozen
simulator-trained MLP chooses which chest to haul to a real destination.

The experiment is OPERATOR-TRIGGERED and runs on a disposable Forge world.
Only direct RCON inventory reads after/before a physical task establish actual
source/destination item transfers. No Create recipe, scientific discovery,
neural online training, or rewards are asserted.
"""
import json
import os
import re
import socket
import struct
import time
from pathlib import Path

def frame(seq, kind, payload):
    body=struct.pack("<ii",seq,kind)+payload.encode()+b"\0\0"
    return struct.pack("<i",len(body))+body

def exact(sock,n):
    b=b""
    while len(b)<n:
        part=sock.recv(n-len(b))
        if not part: raise ConnectionError("RCON connection dropped")
        b+=part
    return b

def read(sock):
    for _ in range(12):
        n=struct.unpack("<i",exact(sock,4))[0]
        if not 10<=n<=1000000: raise ValueError("Bad RCON length")
        raw=exact(sock,n)
        req=struct.unpack("<i",raw[:4])[0]
        out=raw[8:-2].decode(errors="replace")
        if out.strip(): return req,out
    raise RuntimeError("Missing nonempty RCON response")

class Rcon:
    def __enter__(self):
        self.sock=socket.create_connection(("127.0.0.1",25575),timeout=20)
        self.sock.settimeout(20)
        self.sock.sendall(frame(1,3,os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        req,_=read(self.sock)
        if req!=1: req,_=read(self.sock)
        if req!=1: raise ConnectionError("RCON authentication failed")
        self.counter=10
        return self
    def __exit__(self,*args):
        self.sock.close()
    def run(self,command):
        self.counter+=1
        self.sock.sendall(frame(self.counter,2,command))
        req,result=read(self.sock)
        if req!=self.counter: raise AssertionError("RCON response ID mismatch")
        print(f"NEURAL_PHYSICAL_RCON {command} => {result}",flush=True)
        return result
    def require(self,command,needle):
        out=self.run(command)
        if needle.lower() not in out.lower():
            raise AssertionError(f"Expected {needle!r}: {command!r} => {out}")
        return out

def count(r,pos,wheat):
    if wheat==0:
        r.require(f"data get block {pos} Items","block data: []")
    else:
        r.require(f"data get block {pos} Items",f"Count: {wheat}b")

def go():
    # The source observer is NOT the executor. The executor is also the
    # recipient of the report and owner of the policy decision.
    sable="@e[type=minecraft:villager,name=Sable,limit=1]"
    scout="@e[type=minecraft:villager,tag=hb_neural_scout,limit=1]"
    a,b,dest="3 101 1","7 101 1","10 101 2"
    model=Path("run/report-choice-mlp-v1.sha256").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{64}",model):
        raise AssertionError("No preboot pinned trained model")
    choices=f"{sable} {a} {b} {dest}"
    info={"schema":"hearthbound.real-neural-executor-physical-v1",
          "origin":"REAL_FORGE_AUTHORITATIVE_WORLD",
          "model_sha256":model,"policy":"SIMULATOR_TRAINED_FROZEN_MLP",
          "source_a_before":3,"source_b_before":1,
          "destination_before":0,
          "task_executed_by_real_villager":False,
          "physical_transfer_verified":False,
          "rewards_issued":False,"research_credit_issued":False,
          "model_updated":False,"autonomous_planning_claimed":False}
    with Rcon() as r:
        for cmd in (
            "gamerule doMobSpawning false",
            "forceload add 0 0",
            "fill 0 99 0 12 105 4 minecraft:air",
            "fill 0 100 0 12 100 4 minecraft:stone",
            'setblock 3 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]} replace',
            'setblock 7 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]} replace',
            "setblock 10 101 2 minecraft:chest replace",
        ): r.run(cmd)
        r.require("execute positioned 2 101 2 run sable spawn","Sable spawned")
        for _ in range(40):
            if "Test passed" in r.run(f"execute if entity {sable}"): break
            time.sleep(.25)
        else: raise AssertionError("Executor entity never loaded")
        r.require(f"tp {sable} 2 101 2","Teleported")
        scout_spawn=r.run("""summon minecraft:villager 4 101 3 {CustomName:'{"text":"ResourceScout"}',Tags:["hb_neural_scout"],ForgeData:{"hearthbound.citizen":1b},NoAI:1b}""")
        if "Summoned new" not in scout_spawn:
            raise AssertionError("Real marked scout creation failed")
        for _ in range(40):
            if "Test passed" in r.run(f"execute if entity {scout}"): break
            time.sleep(.25)
        else: raise AssertionError("Scout entity never loaded")
        if "status=UNKNOWN" not in r.run(f"hearthbound citizen_memory {a} {sable}"):
            raise AssertionError("Executor started with omniscient direct-source memory")

        before=r.require(f"hearthbound-report-execution {sable} 00000000-0000-4000-8000-000000000001",
                         "status=DENIED reason=NO_MATCHING_NEURAL_TASK")
        no_report=r.require(f"hearthbound-report-dispatch {choices} exposed","status=ABSTAIN")
        if "task_assigned=false" not in no_report:
            raise AssertionError("Neural policy created task without reports")
        r.require(f"execute at {sable} run sable haul-status","No hauling job")

        # A different citizen directly senses the actual source inventories.
        r.require(f"hearthbound citizen_observe {a} {scout}","wheat=3")
        r.require(f"hearthbound citizen_observe {b} {scout}","wheat=1")
        r.require(f"hearthbound-share-direct {a} {scout} {sable}","status=DELIVERED")
        r.require(f"hearthbound-share-direct {b} {scout} {sable}","status=DELIVERED")
        for source in (a,b):
            r.require(f"hearthbound knowledge_report {source} {sable}","status=REPORTED")
            # Incoming scout reports must not become executor direct observation.
            r.require(f"hearthbound citizen_memory {source} {sable}","status=UNKNOWN")
        r.require(f"execute at {sable} run sable haul-status","No hauling job")

        # WITHHELD arm cannot assign a job even though the reports are present.
        blind=r.require(f"hearthbound-report-dispatch {choices} withheld","status=ABSTAIN")
        if "task_assigned=false" not in blind or "job=NONE" not in blind:
            raise AssertionError("Withheld treatment assigned physical work")
        r.require(f"execute at {sable} run sable haul-status","No hauling job")
        count(r,a,3)
        count(r,b,1)
        count(r,dest,0)

        # Freeze policy decision BEFORE touching either inventory. Operator
        # provides candidate menu/destination, not which source is selected.
        shadow=r.require(f"hearthbound-report-mlp-choice {sable} {a} {b} exposed",
                         "status=CHOOSE")
        if "selected=minecraft:overworld|3,101,1" not in shadow:
            raise AssertionError("Frozen MLP shadow did not choose A")
        if "model_sha256="+model not in shadow:
            raise AssertionError("Forge used an unexpected model")
        result=r.require(f"hearthbound-report-dispatch {choices} exposed","status=ASSIGNED")
        for marker in ("source=minecraft:overworld|3,101,1",
                       "decision_origin=OPERATOR_TRIGGERED_FROZEN_POLICY",
                       "policy=SIMULATOR_TRAINED_FROZEN_MLP",
                       "inventory_read=false task_assigned=true",
                       "reward_authorized=false learning_authorized=false",
                       "model_sha256="+model):
            if marker not in result:
                raise AssertionError("Pre-task neural decision was not actually bound: "+result)
        match=re.search(r"\bjob=([a-f0-9-]{36})\b",result)
        if not match: raise AssertionError("No real hauling job UUID in decision")
        job=match.group(1)
        if not re.search(r"\bsource_report_id=\S+",result):
            raise AssertionError("No actual delivered scout report identity")
        info.update({"job":job,"source_selected":"A",
                     "pre_action_decision_receipt":result,
                     "shadow_pre_action_choice":shadow,
                     "withheld_result":blind,
                     "decision_issued_before_outcome":True})

        # Real Minecraft executor moves the item: no /give, /summon item,
        # manual inventory transfer or artificial completion in this script.
        completed=False
        start=time.monotonic()
        last=""
        for i in range(135):
            time.sleep(1)
            last=r.run(f"hearthbound-report-execution {sable} {job}")
            if "status=EXECUTOR_COMPLETED" in last:
                completed=True
                break
            if "status=DENIED" in last:
                raise AssertionError("Executor attribution invalid: "+last)
            if i%15==0:
                audit=r.run(f"execute at {sable} run sable haul-audit")
                if "QUARANTINED" in audit or "phase=3" in audit or "phase=4" in audit:
                    raise AssertionError("Real hauling job failed: "+audit)
        if not completed:
            audit=r.run(f"execute at {sable} run sable haul-audit")
            pos=r.run(f"data get entity {sable} Pos")
            raise AssertionError("Neural-selected physical haul timeout: "+last+" "+audit+" "+pos)
        # CompletedJob alone is not proof of the verified inventory deltas:
        # the operator must independently check both physical endpoint chests.
        count(r,a,2)
        count(r,b,1)
        count(r,dest,1)
        if "inventory_delta_verified=false" not in last:
            raise AssertionError("Executor audit falsely claimed independent physical inventory proof")
        info.update({"executor_completion_receipt":last,
                     "source_a_after":2,"source_b_after":1,
                     "destination_after":1,"task_executed_by_real_villager":True,
                     "physical_transfer_verified":True,
                     "wall_seconds_to_completed_receipt":round(time.monotonic()-start,3),
                     "rewards_issued":False,"model_updated":False})
        Path("real-neural-report-haul-results.json").write_text(
            json.dumps(info,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print("REAL_FORGE_FROZEN_MLP_PHYSICAL_HAUL_PASS "
              "source_A=3_to_2 source_B=1_to_1 dest=0_to_1 "
              "executor_completed=true report_owner_equals_executor=true "
              "withheld_abstained=true neural_model_sha256="+model+" "
              "reward_authorized=false learning_authorized=false",flush=True)

if __name__=="__main__":
    go()
