#!/usr/bin/env python3
"""Chronology-safe offline replay of verified real Forge perception receipts.

Does not rerun Minecraft, infer unseen source contents, create counterfactual
actions, or label rewards. This audit accepts validated receipt JSON only.
"""
import argparse
import hashlib
import json
from pathlib import Path

SCHEMA="hearthbound.real-forge-chronological-replay.v1"
INPUT_SCHEMA="hearthbound.live-perception-replay-validation.v1"

def replay(data):
    if data.get("schema")!=INPUT_SCHEMA or data.get("task_execution_authorized") is not False:
        raise ValueError("Untrusted or unauthorized receipt validation")
    events=data.get("events")
    if not isinstance(events,list) or not events:
        raise ValueError("No verified source observations")
    if data.get("receipts")!=len(events):
        raise ValueError("Receipt count differs from event count")
    history={}
    timelines=[]
    last_global=-1
    last_revision={}
    for event in events:
        if not isinstance(event,dict):raise ValueError("Invalid event")
        required=("schema","dimension","source","revision","tick","state","wheat",
                  "observer","evidence","action_authorized")
        if set(event)!=set(required) or event["action_authorized"]!="false":
            raise ValueError("Invalid receipt fields or action authority")
        if event["schema"]!="hearthbound.live-perception-receipt.v1" or event["evidence"]!="REAL_FORGE_SOURCE_OBSERVATION":
            raise ValueError("Wrong evidence")
        tick=event["tick"]
        if type(tick)!=int or tick<0 or tick<last_global:
            raise ValueError("Future-to-past receipt order or invalid tick")
        if type(event["revision"])!=int or event["revision"]<1 or type(event["wheat"])!=int:
            raise ValueError("Invalid revision or inventory quantity")
        if event["state"] not in ("EMPTY","AVAILABLE") or (event["state"]=="EMPTY")!=(event["wheat"]==0):
            raise ValueError("Inconsistent inventory state")
        key=(event["observer"],event["dimension"],event["source"])
        old_rev=last_revision.get(key)
        if old_rev is not None and event["revision"]!=old_rev+1:
            raise ValueError("Missing or non-increasing source revision")
        before=history.get(key)
        if before is not None and before["state"]==event["state"] and before["wheat"]==event["wheat"]:
            raise ValueError("Change-only receipt repeated unchanged source")
        # before captures *only* observations from earlier rows in the
        # recorded timeline. No future or other-citizen observations.
        prior=({"status":"UNKNOWN","known_wheat":None,"age_ticks":None,
                "observed_changes":0,"observations":0}
               if before is None else
               {"status":"KNOWN","known_wheat":before["wheat"],
                "age_ticks":tick-before["tick"],
                "observed_changes":before["changes"],
                "observations":before["count"]})
        count=1 if before is None else before["count"]+1
        changes=0 if before is None else before["changes"]+int(before["state"]!=event["state"] or before["wheat"]!=event["wheat"])
        history[key]={"tick":tick,"state":event["state"],"wheat":event["wheat"],
                      "changes":changes,"count":count}
        timelines.append({"decision_tick":tick,
                          "observer":key[0],"dimension":key[1],"source":key[2],
                          "before_receipt":prior,
                          "observed":{"state":event["state"],"wheat":event["wheat"],
                                      "revision":event["revision"]},
                          "after_receipt":{"known_wheat":event["wheat"],
                                           "observations":count,"observed_changes":changes},
                          "counterfactual_reward_available":False,
                          "action_authorized":False})
        last_global=tick
        last_revision[key]=event["revision"]
    report={"schema":SCHEMA,"origin":"REAL_FORGE_VERIFIED_RECEIPTS",
            "training_performed":False,
            "minecraft_execution_authorized":False,
            "counterfactual_outcomes_inferred":False,
            "events":len(timelines),"distinct_observer_sources":len(history),
            "timeline":timelines}
    canonical=json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False)
    report["sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,default=Path("real-forge-shadow-timeline.json"))
    args=parser.parse_args()
    report=replay(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("REAL_FORGE_CHRONOLOGICAL_SHADOW", "events="+str(report["events"]),
          "observer_sources="+str(report["distinct_observer_sources"]),
          "training=false execution=false counterfactual=false")

if __name__=="__main__":
    main()
