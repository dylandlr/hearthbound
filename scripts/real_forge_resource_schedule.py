#!/usr/bin/env python3
"""Deterministic, bounded RCON resource interventions in disposable Forge worlds.

Schedules specify interventions, not citizen observations or outcomes. The
server is the authority on whether each mutation succeeded and its tick.
"""
import hashlib
import json
import re

SCHEMA="hearthbound.forge-resource-intervention-schedule.v1"
SOURCES=("9 100 2","10 100 2")
START_COUNTS=(3,1)
MAX_STEPS=6

def plan(seed,variant="seeded-v1"):
    if variant!="seeded-v1" or not isinstance(seed,str) or not 1<=len(seed)<=128:
        raise ValueError("unsupported seeded schedule")
    if any(c in seed for c in "\r\n\x00"):
        raise ValueError("invalid world seed")
    last=list(START_COUNTS)
    steps=[]
    for i in range(MAX_STEPS):
        slot=i%2
        # Deliberately alternate sources and ensure a changed inventory NBT
        # in each intervention. Counts are a deterministic function of seed.
        raw=hashlib.sha256((SCHEMA+"|"+seed+"|"+str(i)).encode()).digest()
        new=raw[0]%5
        if new==last[slot]:
            new=(new+1)%5
        last[slot]=new
        steps.append({"index":i+1,"source":SOURCES[slot],
                      "wheat":new,"delay_seconds":0.40})
    document={"schema":SCHEMA,"variant":variant,"configured_world_seed":seed,
              "base_fixture":"chest-two-source-v1",
              "initial_wheat":dict(zip(SOURCES,START_COUNTS)),
              "steps":steps,"source_count":2,
              "actual_server_observations_inferred":False,
              "minecraft_agent_actions_authorized":False}
    canonical=json.dumps(document,sort_keys=True,separators=(",",":"),allow_nan=False)
    document["sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    return document

def command(step):
    source=step["source"]
    if source not in SOURCES or type(step["wheat"])!=int or not 0<=step["wheat"]<=4:
        raise ValueError("invalid intervention")
    x,y,z=source.split()
    # A direct operator-authored mutation, NOT a citizen action. It changes
    # the controlled source fixture in the disposable server only.
    items=("[]" if step["wheat"]==0 else
           '[{Slot:0b,id:"minecraft:wheat",Count:'+str(step["wheat"])+'b}]')
    return "data merge block "+x+" "+y+" "+z+" {Items:"+items+"}"

def validate_log(document):
    if not isinstance(document,dict) or document.get("schema")!=SCHEMA:
        raise ValueError("invalid intervention report")
    if document.get("origin")!="REAL_FORGE_RCON":
        raise ValueError("schedule was not executed against real RCON")
    base=plan(document.get("configured_world_seed"),"seeded-v1")
    if document.get("schedule_sha256")!=base["sha256"]:
        raise ValueError("schedule/seed digest mismatch")
    events=document.get("executions")
    if not isinstance(events,list) or len(events)!=len(base["steps"]):
        raise ValueError("missing or extra interventions")
    previous_tick=-1
    for expected,actual in zip(base["steps"],events):
        if (not isinstance(actual,dict) or
            set(actual)!={"index","source","wheat","tick_before","tick_after","status"}):
            raise ValueError("invalid actual intervention event")
        if any(actual[k]!=expected[k] for k in ("index","source","wheat")):
            raise ValueError("intervention does not match precommitted plan")
        if (type(actual["tick_before"])!=int or type(actual["tick_after"])!=int
            or actual["tick_before"]<previous_tick
            or actual["tick_before"]>actual["tick_after"]
            or actual["status"]!="RCON_MODIFIED"):
            raise ValueError("nonmonotonic or unverified server intervention")
        previous_tick=actual["tick_after"]
    # The explicit measurement cutoff is recorded BEFORE any fixture cleanup.
    # Absence remains supported for older intervention logs, but gives no
    # post-final-intervention coverage window.
    cutoff=document.get("measurement_stop_tick")
    if cutoff is not None and (
        type(cutoff)!=int or cutoff<=previous_tick
    ):
        raise ValueError("measurement cutoff must follow final mutation")
    if document.get("counterfactual_outcomes_inferred") is not False:
        raise ValueError("unauthorized counterfactual claim")
    return {"schema":"hearthbound.verified-forge-resource-schedule.v1",
            "origin":"REAL_FORGE_RCON",
            "configured_world_seed":base["configured_world_seed"],
            "schedule_sha256":base["sha256"],
            "verified_interventions":len(events),
            "measurement_stop_tick":cutoff,
            "actual_agent_learning_claimed":False,
            "counterfactual_outcomes_inferred":False}

if __name__=="__main__":
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",required=True)
    parser.add_argument("--output",type=Path,default=Path("resource-schedule-plan.json"))
    options=parser.parse_args()
    options.output.write_text(json.dumps(plan(options.seed),indent=2,sort_keys=True)+"\n")
    print("FORGE_SEEDED_RESOURCE_SCHEDULE_PLANNED origin=SIMULATED_INTERVENTION_PLAN_ONLY")
