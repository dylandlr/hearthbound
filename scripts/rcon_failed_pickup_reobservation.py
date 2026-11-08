#!/usr/bin/env python3
"""Real Forge failed-source feedback and recovery, with actual physical item transfer.

Operator-triggered experiment: an independent scout reports A=3/B=1; A is
emptied after communication; Sable selects A and genuinely fails extracting;
a server-side job-bound negative event prevents A's stale report replay;
a real scout reobserves A=0 and reports it; after safe no-cargo cancellation,
Sable chooses B and the real motor delivers its wheat.

No task-success counterfactual, research reward, model training, or LLM.
"""
import json
import os
import re
import time
from pathlib import Path
from rcon_neural_report_haul import Rcon

EX="@e[type=minecraft:villager,name=Sable,limit=1]"
SCOUT="@e[type=minecraft:villager,tag=hb_failure_scout,limit=1]"
A,B,D="3 101 1","7 101 1","10 101 2"
MENU=f"{EX} {A} {B} {D}"

def check_count(r,pos,count):
    x=r.run(f"data get block {pos} Items")
    if count==0:
        if "block data: []" not in x: raise AssertionError("Not an actually empty chest: "+x)
    elif f"Count: {count}b" not in x or 'minecraft:wheat' not in x:
        raise AssertionError("Unexpected physical wheat count: "+x)

def require(r,cmd,expected):
    return r.require(cmd,expected)

def main():
    model=Path("run/report-choice-mlp-v1.sha256").read_text().strip()
    if not re.fullmatch("[a-f0-9]{64}",model):
        raise AssertionError("Model must be frozen before boot")
    outcome={
        "schema":"hearthbound.real-failed-pickup-reobservation.v1",
        "origin":"REAL_FORGE_EXTRACTOR_AND_CHEST",
        "model_sha256":model,
        "operator_triggered":True,
        "negative_evidence_source":"ACTUAL_EXTRACTION_RETURNED_EMPTY",
        "source_empty_inferred_from_timeout":False,
        "original_report_preserved":True,
        "research_reward_authorized":False,
        "gradient_update_authorized":False,
        "technology_unlocked":False,
        "first_attempt_delivered":False,
        "recovery_delivered":False,
    }
    with Rcon() as r:
        for command in (
            "gamerule doMobSpawning false",
            "forceload add 0 0",
            "fill 0 99 0 12 105 4 minecraft:air",
            "fill 0 100 0 12 100 4 minecraft:stone",
            'setblock 3 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]} replace',
            'setblock 7 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]} replace',
            "setblock 10 101 2 minecraft:chest replace"):
            r.run(command)
        require(r,"execute positioned 2 101 2 run sable spawn","Sable spawned")
        for _ in range(40):
            if "Test passed" in r.run(f"execute if entity {EX}"): break
            time.sleep(.25)
        else: raise AssertionError("No real executor villager after spawn")
        require(r,f"tp {EX} 2 101 2","Teleported")
        require(r,"""summon minecraft:villager 4 101 3 {CustomName:'{"text":"FailureScout"}',Tags:["hb_failure_scout"],ForgeData:{"hearthbound.citizen":1b},NoAI:1b}""","Summoned new")
        for _ in range(40):
            if "Test passed" in r.run(f"execute if entity {SCOUT}"): break
            time.sleep(.25)
        else: raise AssertionError("No independent real scout after spawn")
        if "state=NONE" not in require(r,f"hearthbound-pickup-belief {EX} {A}","state=NONE"):
            raise AssertionError("Invented failed pickup before first task")
        early=r.run(f"hearthbound-reobserve-request {EX} {A}")
        if "No real extraction miss available" not in early:
            raise AssertionError("Unproven recheck request was admitted: "+early)

        require(r,f"hearthbound citizen_observe {A} {SCOUT}","wheat=3")
        require(r,f"hearthbound citizen_observe {B} {SCOUT}","wheat=1")
        require(r,f"hearthbound-share-direct {A} {SCOUT} {EX}","status=DELIVERED")
        require(r,f"hearthbound-share-direct {B} {SCOUT} {EX}","status=DELIVERED")
        # Adversarial source change AFTER delivered reports, no omniscient input.
        require(r,f"data modify block {A} Items set value []","Modified block data")
        check_count(r,A,0)
        check_count(r,B,1)
        check_count(r,D,0)

        old=r.run(f"hearthbound-report-choice {EX} {A} {B} exposed")
        if "selected=minecraft:overworld|3,101,1" not in old:
            raise AssertionError("The old report was not available for failed physical trial: "+old)
        assigned=require(r,f"hearthbound-report-dispatch-trial {MENU} SCRIPTED exposed",
                         "status=ASSIGNED")
        if "source=minecraft:overworld|3,101,1" not in assigned:
            raise AssertionError("Old report did not select source A: "+assigned)
        job=re.search(r"\bjob=([a-f0-9-]{36})",assigned)
        if not job: raise AssertionError("No real failed job UUID")
        job=job.group(1)
        outcome["first_job"]=job
        outcome["first_assignment"]=assigned

        failed=False
        deadline=time.monotonic()+70
        while time.monotonic()<deadline:
            evidence=r.run(f"hearthbound-pickup-belief {EX} {A}")
            if "state=FAIL_CLOSED" in evidence:
                raise AssertionError("Invalid/overflowed negative evidence: "+evidence)
            if "state=PICKUP_RETURNED_EMPTY" in evidence:
                if "job="+job not in evidence or "source_empty_verified=false" not in evidence:
                    raise AssertionError("Failed extraction lacked independent job provenance: "+evidence)
                failed=True
                outcome["failed_pickup_receipt"]=evidence
                break
            time.sleep(.5)
        if not failed:
            raise AssertionError("Real motor never reached source extraction, failure cannot be claimed")
        actual=require(r,f"hearthbound-report-execution {EX} {job}","status=INCOMPLETE")
        if "executor_state=Paused:" not in actual:
            raise AssertionError("Failed extraction was confused with another motor event: "+actual)
        audit=r.run(f"execute at {EX} run sable haul-audit")
        if "No wheat available" not in audit:
            raise AssertionError("Pickup failure not verified by real motor: "+audit)
        outcome["failed_motor_audit"]=audit

        # At the exact decision boundary, no new reports have been sent:
        # Sable must reject A's still-remembered 3-wheat observation.
        new_choice=r.run(f"hearthbound-report-choice {EX} {A} {B} exposed")
        if "selected=minecraft:overworld|7,101,1" not in new_choice:
            raise AssertionError("Stale report re-entered scripted action menu: "+new_choice)
        # Explicit request for re-observation, but NOT an automatic remote read.
        request=require(r,f"hearthbound-reobserve-request {EX} {A}","status=REQUESTED")
        if "scout_observed=false" not in request:
            raise AssertionError("Request faked a scout observation")
        outcome["request_receipt"]=request
        old_replay=r.run(f"hearthbound-share-direct {A} {SCOUT} {EX}")
        if "status=DUPLICATE" not in old_replay:
            raise AssertionError("Original direct observation was replayed as new evidence: "+old_replay)
        await_report=require(r,f"hearthbound-pickup-belief {EX} {A}",
                             "reobservation_request=AWAITING_SCOUT_DIRECT_OBSERVATION")
        # No cargo was ever picked up. Cancellation releases the original
        # claim; no teleportation, synthetic transfer or reconciliation hack.
        require(r,f"execute at {EX} run sable haul-cancel","Unpicked haul cancelled")
        check_count(r,A,0)
        check_count(r,B,1)
        check_count(r,D,0)

        # A real separate scout makes a NEW direct observation of A's changed
        # physical state. Only that actual direct read can fulfill the request.
        refreshed=require(r,f"hearthbound citizen_observe {A} {SCOUT}","wheat=0")
        if "state=EMPTY" not in refreshed:
            raise AssertionError("Scout did not directly observe the real empty A")
        new_share=require(r,f"hearthbound-share-direct {A} {SCOUT} {EX}","status=DELIVERED")
        fulfilled=require(r,f"hearthbound-pickup-belief {EX} {A}",
                          "reobservation_request=FULFILLED_BY_NEW_DIRECT_REPORT")
        outcome["new_scout_report"]=new_share
        outcome["request_fulfilled"]=fulfilled
        if "status=REPORTED" not in r.run(f"hearthbound knowledge_report {A} {EX}"):
            raise AssertionError("Source A update not retained in recipient-only report history")

        # Replan on remaining B report and physically deliver its single wheat.
        switched=require(r,f"hearthbound-report-dispatch-trial {MENU} SCRIPTED exposed",
                         "status=ASSIGNED")
        if "source=minecraft:overworld|7,101,1" not in switched:
            raise AssertionError("Recovery replan did not choose still-available B: "+switched)
        successor=re.search(r"\bjob=([a-f0-9-]{36})",switched)
        if not successor or successor.group(1)==job:
            raise AssertionError("Recovery did not mint new physically assigned job")
        successor=successor.group(1)
        outcome["second_job"]=successor
        outcome["second_assignment"]=switched
        delivered=False
        deadline=time.monotonic()+85
        while time.monotonic()<deadline:
            receipt=r.run(f"hearthbound-report-execution {EX} {successor}")
            if "status=DENIED" in receipt:
                raise AssertionError("Second job provenance lost: "+receipt)
            if "status=EXECUTOR_COMPLETED" in receipt:
                outcome["second_completion"]=receipt
                delivered=True
                break
            time.sleep(.75)
        if not delivered:
            position=r.run(f"data get entity {EX} Pos")
            raise AssertionError("Real B recovery haul did not finish: "+position)
        check_count(r,A,0)
        check_count(r,B,0)
        check_count(r,D,1)
        # The original *failed* pickup never receives a completion receipt.
        final_belief=require(r,f"hearthbound-pickup-belief {EX} {A}",
                             "state=PICKUP_RETURNED_EMPTY")
        if "job="+job not in final_belief:
            raise AssertionError("Replacing the hauling task erased original failure")
        outcome["recovery_delivered"]=True
        outcome["authoritative_endpoints"]={"A":0,"B":0,"destination":1}
        outcome["first_attempt_delivered"]=False
        Path("real-failed-pickup-reobservation-results.json").write_text(
            json.dumps(outcome,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print("REAL_FORGE_FAILED_PICKUP_REOBSERVATION_PASS "
              "real_failed_A=true original_report_suppressed=true "
              "new_direct_report_delivered=true negative_event_retained=true "
              "real_B_delivered=true rewards=0 model_updates=0",flush=True)

if __name__=="__main__":
    main()
