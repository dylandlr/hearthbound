#!/usr/bin/env python3
"""Precommitted rapid four-source operator interventions for disposable Forge.

This is a controlled fixture schedule, not natural source dynamics or AI
actions. The selected citizen can inspect at most one of four sources per
five Minecraft ticks; rapid state changes may be missed.
"""
import hashlib
import json

SCHEMA="hearthbound.rapid-four-resource-plan.v1"
SOURCES=("7 100 2","9 100 2","11 100 2","13 100 2")
INITIAL=(1,2,3,4)
STEPS=16

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def plan(seed):
    if not isinstance(seed,str) or not 1<=len(seed)<=128 or any(c in seed for c in "\r\n\x00"):
        raise ValueError("invalid configured seed")
    last=dict(zip(SOURCES,INITIAL))
    steps=[]
    for index in range(STEPS):
        # Uneven exposure: source 7 changes more frequently. The selected
        # candidate list is always all four sources, and this plan contains
        # zero information about which source an agent will inspect.
        slot=(0,0,1,2,0,3,1,0,2,3,0,1,3,0,2,1)[index]
        source=SOURCES[slot]
        raw=hashlib.sha256((SCHEMA+"|"+seed+"|"+str(index)).encode()).digest()
        count=raw[0]%5
        if count==last[source]:count=(count+1)%5
        last[source]=count
        steps.append({"index":index+1,"source":source,"wheat":count,
                      "pause_seconds":0.11})
    value={"schema":SCHEMA,"configured_world_seed":seed,
           "fixture_id":"rapid-four-source-v1",
           "sources":list(SOURCES),
           "initial_wheat":dict(zip(SOURCES,INITIAL)),
           "steps":steps,
           "policy_has_hidden_source_truth":False,
           "resource_changes_operator_authored":True,
           "agent_actions_authorized":False}
    value["sha256"]=digest(value)
    return value

def rcon_command(source,wheat):
    if source not in SOURCES or type(wheat)!=int or not 0<=wheat<=4:
        raise ValueError("invalid resource mutation")
    content=("[]" if wheat==0 else
             '[{Slot:0b,id:"minecraft:wheat",Count:'+str(wheat)+'b}]')
    return "data merge block "+source+" {Items:"+content+"}"

def verify(actual):
    if (not isinstance(actual,dict) or actual.get("origin")!="REAL_FORGE_RCON"
        or actual.get("schema")!="hearthbound.rapid-four-resource-execution.v1"
        or actual.get("counterfactual_outcomes_inferred") is not False):
        raise ValueError("unverified real four-source intervention log")
    planned=plan(actual.get("configured_world_seed"))
    if actual.get("plan_sha256")!=planned["sha256"]:
        raise ValueError("plan hash does not match seed")
    events=actual.get("executions")
    if not isinstance(events,list) or len(events)!=STEPS:raise ValueError("missing interventions")
    previous=-1
    for expected,item in zip(planned["steps"],events):
        if (not isinstance(item,dict)
            or set(item)!={"index","source","wheat","tick_before","tick_after","status"}
            or any(item.get(k)!=expected[k] for k in ("index","source","wheat"))
            or item.get("status")!="RCON_MODIFIED"
            or type(item.get("tick_before"))!=int
            or type(item.get("tick_after"))!=int
            or item["tick_before"]<previous
            or item["tick_after"]<item["tick_before"]):
            raise ValueError("invalid server RCON evidence")
        previous=item["tick_after"]
    stop=actual.get("measurement_stop_tick")
    if type(stop)!=int or stop<=previous:
        raise ValueError("missing pre-cleanup cutoff")
    return {"schema":"hearthbound.verified-rapid-four-execution.v1",
            "origin":"REAL_FORGE_RCON",
            "configured_world_seed":planned["configured_world_seed"],
            "plan_sha256":planned["sha256"],
            "verified_interventions":STEPS,
            "measurement_stop_tick":stop,
            "counterfactual_outcomes_inferred":False}

if __name__=="__main__":
    import argparse
    from pathlib import Path
    cli=argparse.ArgumentParser()
    cli.add_argument("--seed",required=True)
    cli.add_argument("--output",type=Path,default=Path("rapid-four-plan.json"))
    args=cli.parse_args()
    args.output.write_text(json.dumps(plan(args.seed),sort_keys=True,indent=2)+"\n")
    print("RAPID_FOUR_PLAN frozen=true mutations_not_executed=true")
