#!/usr/bin/env python3
"""v0.16.4 paired *physical* Minecraft trial. One arm, one disposable world.

Operator prepares identical inventories for both policies, with the same seed
and a second scout's *real* direct-source report. The selected source is
determined by the policy and never by the operator. Outcomes are measured
from the real chest inventories, not guessed from decision logits or motor NBT.

Failure, abstention, and stuck routing are RECORDED, not papered over. An
unexpected evidence-contract violation still fails CI. No research rewards.
"""
import argparse
import json
import os
import re
import time
from pathlib import Path
from rcon_neural_report_haul import Rcon

A, B, DEST = "3 101 1", "7 101 1", "10 101 2"
SABLE = "@e[type=minecraft:villager,name=Sable,limit=1]"
SCOUT = "@e[type=minecraft:villager,tag=hb_matched_scout,limit=1]"
POLICIES = {"SCRIPTED":"SCRIPTED_REPORT_RANK_V1",
            "FROZEN_MLP":"SIMULATOR_TRAINED_FROZEN_MLP"}

def expect(read, fragment):
    if fragment not in read:
        raise AssertionError("Missing verifiable Minecraft evidence " + fragment + " :: " + read)
    return read

def count(r, position):
    output = r.run(f"data get block {position} Items")
    # Single-item-type fixture; any other NBT is an integrity failure.
    if "block data: []" in output:
        return 0
    match = re.search(r'id: "minecraft:wheat", Count: (\d+)b', output)
    if not match:
        match = re.search(r'Count: (\d+)b, id: "minecraft:wheat"', output)
    if not match:
        raise AssertionError("Cannot independently verify wheat-only chest: " + output)
    return int(match.group(1))

def report_time(r):
    output = r.run("time query gametime")
    m = re.search(r"(\d+)\s*$", output)
    if not m:
        raise AssertionError("Cannot read authoritative server gametime: " + output)
    return int(m.group(1))

def unchanged(before, after):
    if before != after:
        raise AssertionError("Control decision mutated physical Minecraft inventory")

def trial(args):
    if args.policy not in POLICIES: raise ValueError("unknown policy")
    if args.scenario not in ("fresh", "unannounced_depletion"):
        raise ValueError("unknown scenario")
    modelsha=Path("run/report-choice-mlp-v1.sha256").read_text().strip()
    if not re.fullmatch(r"[0-9a-f]{64}",modelsha):
        raise AssertionError("Model must be frozen before trial")
    result = {
        "schema":"hearthbound.matched-real-physical-haul.v1",
        "evidence_origin":"REAL_FORGE_WORLD_INVENTORY",
        "seed":args.seed,"policy":args.policy,
        "scenario":args.scenario,"model_sha256":modelsha,
        "training_includes_this_world":False,
        "scout_distinct_from_executor":True,
        "operator_triggered":True,"no_model_updates":True,
        "research_reward_authorized":False,"technology_unlocked":False,
        "inventory_delta_verified":False,
        "physical_success":False,"status":"NOT_STARTED",
    }
    choice=f"{SABLE} {A} {B} {DEST} {args.policy}"
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
        expect(r.run("execute positioned 2 101 2 run sable spawn"), "Sable spawned")
        for _ in range(40):
            if "Test passed" in r.run(f"execute if entity {SABLE}"): break
            time.sleep(.25)
        else: raise AssertionError("Executor absent after spawn")
        expect(r.run(f"tp {SABLE} 2 101 2"),"Teleported")
        expect(r.run("""summon minecraft:villager 4 101 3 {CustomName:'{"text":"MatchedResourceScout"}',Tags:["hb_matched_scout"],ForgeData:{"hearthbound.citizen":1b},NoAI:1b}"""),"Summoned new")
        for _ in range(40):
            if "Test passed" in r.run(f"execute if entity {SCOUT}"): break
            time.sleep(.25)
        else: raise AssertionError("Scout absent after spawn")
        if "status=UNKNOWN" not in r.run(f"hearthbound citizen_memory {A} {SABLE}"):
            raise AssertionError("Executor has a direct source observation prior to communication")
        # Negative controls cannot cause a physical job.
        expect(r.run(f"hearthbound-report-dispatch-trial {choice} exposed"),"status=ABSTAIN")
        expect(r.run(f"execute at {SABLE} run sable haul-status"),"No hauling job")
        expect(r.run(f"hearthbound citizen_observe {A} {SCOUT}"),"wheat=3")
        expect(r.run(f"hearthbound citizen_observe {B} {SCOUT}"),"wheat=1")
        share_a=expect(r.run(f"hearthbound-share-direct {A} {SCOUT} {SABLE}"),"status=DELIVERED")
        share_b=expect(r.run(f"hearthbound-share-direct {B} {SCOUT} {SABLE}"),"status=DELIVERED")
        for src in (A,B):
            expect(r.run(f"hearthbound knowledge_report {src} {SABLE}"),"status=REPORTED")
            expect(r.run(f"hearthbound citizen_memory {src} {SABLE}"),"status=UNKNOWN")
        result["scout_report_receipts"]=[share_a,share_b]

        if args.scenario=="unannounced_depletion":
            # This is an operator-controlled world intervention, held exactly
            # equal in both arms. It occurs *after* reports were delivered.
            # A learner must not silently receive the current chest count.
            expect(r.run(f"data modify block {A} Items set value []"),
                   "Modified block data")
        before={"A":count(r,A),"B":count(r,B),"destination":count(r,DEST)}
        expected=({"A":3,"B":1,"destination":0} if args.scenario=="fresh"
                  else {"A":0,"B":1,"destination":0})
        unchanged(expected,before)
        withheld=expect(r.run(f"hearthbound-report-dispatch-trial {choice} withheld"),"status=ABSTAIN")
        expect(withheld,"task_assigned=false")
        expect(r.run(f"execute at {SABLE} run sable haul-status"),"No hauling job")
        unchanged(before,{"A":count(r,A),"B":count(r,B),"destination":count(r,DEST)})
        result["withheld_control_receipt"]=withheld
        result["before"]=before
        decision_start=report_time(r)
        wall_start=time.monotonic()
        assignment=r.run(f"hearthbound-report-dispatch-trial {choice} exposed")
        result["decision_wall_seconds"]=round(time.monotonic()-wall_start,4)
        result["decision_server_tick"]=decision_start
        expect(assignment, "reward_authorized=false learning_authorized=false")
        expect(assignment, "inventory_read=false")
        result["pre_action_receipt"]=assignment
        if "status=ABSTAIN" in assignment:
            expect(assignment,"job=NONE")
            result["selected"]="NONE"
            result["status"]="ABSTAIN"
            result["failure_reason"]="NONE"
            after={"A":count(r,A),"B":count(r,B),"destination":count(r,DEST)}
            unchanged(before,after)
            result["after"]=after
            result["completed_server_ticks"]=0
        else:
            expect(assignment,"status=ASSIGNED")
            expect(assignment, f"policy={POLICIES[args.policy]}")
            if args.policy=="FROZEN_MLP":
                expect(assignment,"model_sha256="+modelsha)
            else:
                expect(assignment,"model_sha256=SCRIPTED_NO_MODEL")
            match=re.search(r"\bjob=([0-9a-f-]{36})\b",assignment)
            if match is None:
                raise AssertionError("No verifiable physical Minecraft job UUID")
            job=match.group(1)
            if "source=minecraft:overworld|3,101,1" in assignment:
                selected="A"
            elif "source=minecraft:overworld|7,101,1" in assignment:
                selected="B"
            else:
                raise AssertionError("Action was not bound to exactly one source")
            result["job"]=job
            result["selected"]=selected
            result["status"]="INCOMPLETE"
            deadline=time.monotonic()+70
            audit=""
            observed=[]
            while time.monotonic()<deadline:
                receipt=r.run(f"hearthbound-report-execution {SABLE} {job}")
                observed.append(receipt)
                if "status=DENIED" in receipt:
                    raise AssertionError("Executor provenance lost while executing: "+receipt)
                if "status=EXECUTOR_COMPLETED" in receipt:
                    result["status"]="EXECUTOR_COMPLETED"
                    result["completion_receipt"]=receipt
                    break
                if "status=INCOMPLETE" not in receipt:
                    raise AssertionError("Unknown physical motor state: "+receipt)
                if "executor_state=Paused" in receipt or "executor_state=QUARANTINED" in receipt:
                    result["status"]="PAUSED_OR_QUARANTINED"
                    result["failure_reason"]="MOTOR_PAUSED_OR_QUARANTINED"
                    break
                time.sleep(1)
            else:
                result["status"]="TIMEOUT"
                result["failure_reason"]="PHYSICAL_HAUL_TIMEOUT"
            if result["status"]!="EXECUTOR_COMPLETED":
                audit=r.run(f"execute at {SABLE} run sable haul-audit")
                result["read_only_motor_audit"]=audit
                result["read_only_executor_position"]=r.run(f"data get entity {SABLE} Pos")
            end=report_time(r)
            after={"A":count(r,A),"B":count(r,B),"destination":count(r,DEST)}
            result["after"]=after
            result["completed_server_ticks"]=max(0,end-decision_start)
            changed=({selected:before[selected]-1,
                      "destination":before["destination"]+1})
            unused="B" if selected=="A" else "A"
            verified=(result["status"]=="EXECUTOR_COMPLETED" and
                      before[selected]>0 and after[selected]==changed[selected] and
                      after[unused]==before[unused] and
                      after["destination"]==changed["destination"])
            if result["status"]=="EXECUTOR_COMPLETED" and not verified:
                raise AssertionError("Executor completed without independently verified physical delta")
            result["physical_success"]=verified
            result["inventory_delta_verified"]=verified
            if not verified and "failure_reason" not in result:
                result["failure_reason"]="NOT_PHYSICALLY_COMPLETE"
            result["last_motor_receipt"]=observed[-1] if observed else "NONE"

        # Pre-registered utility on *actual* Minecraft outcomes. One item
        # delivered = +1; attempted but failed = -0.5; abstain = 0.
        result["utility"]=(
            1.0 if result["physical_success"] else
            0.0 if result["status"]=="ABSTAIN" else -0.5)
        result["completed_item_count"]=int(result["physical_success"])
        result["chest_counts_independently_read"]=True
        result["world_seed_prescribed"]=True
        result["no_training_or_rewards"]=True
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
        print("REAL_FORGE_MATCHED_PHYSICAL_TRIAL_RECEIPT",
              f"policy={args.policy} seed={args.seed} scenario={args.scenario}"
              f" status={result['status']} success={result['physical_success']}"
              f" choice={result['selected']} utility={result['utility']}"
              " research_credit=0 model_updated=false",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--policy",choices=sorted(POLICIES),required=True)
    p.add_argument("--seed",type=int,required=True)
    p.add_argument("--scenario",choices=["fresh","unannounced_depletion"],required=True)
    p.add_argument("--output",type=Path,required=True)
    trial(p.parse_args())
