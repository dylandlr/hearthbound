#!/usr/bin/env python3
"""Export strictly causal citizen attention decisions from finalized real Forge runs.

This is a read-only, on-policy historical dataset. Unselected source outcomes
are NEVER inferred. The file is not a supervised choice-optimality dataset.
"""
import argparse
import base64
import hashlib
import json
from pathlib import Path

from validate_forge_attention_manifest import verify as verify_manifest
from validate_forge_attention_pair import pair

SCHEMA="hearthbound.verified-citizen-experience.v1"

def decode_pair(row):
    encoded=row["payload_b64"]
    raw=base64.urlsafe_b64decode(encoded+"="*((-len(encoded))%4)).decode("utf-8")
    before,after=raw.split("\n")
    return pair(before,after)

def export(journal:Path, manifest:Path, minimum=1):
    verified=verify_manifest(journal,manifest,minimum=minimum)
    records=[json.loads(line) for line in journal.read_text().splitlines()]
    # A citizen can only observe their own selected source. No global cache.
    memory={}
    transitions=[]
    last_tick=-1
    for row in records:
        event=decode_pair(row)
        choice=event["opportunity"]
        outcome=event["outcome"]
        tick=choice["tick"]
        if tick<last_tick:raise ValueError("nonchronological choice")
        last_tick=tick
        citizen=choice["observer"]
        dimension=choice["dimension"]
        candidates=choice["candidates"]
        if not candidates or choice["selected"] not in candidates:
            raise ValueError("invalid candidate list")
        before=[]
        for source in candidates:
            key=(citizen,dimension,source)
            observed=memory.get(key)
            before.append({
                "source":source,
                "status":"UNKNOWN" if observed is None else "KNOWN",
                "last_observed_available":None if observed is None else observed["wheat"]>0,
                "last_observed_wheat":None if observed is None else observed["wheat"],
                "age_ticks":None if observed is None else tick-observed["tick"],
                "direct_observation_count":0 if observed is None else observed["count"],
                "observed_change_count":0 if observed is None else observed["changes"],
                "observed_change_rate":None if observed is None or observed["count"]<2
                    else round(observed["changes"]/(observed["count"]-1),8)
            })
        selected=choice["selected"]
        # Outcomes of all unselected candidates are unavailable by design.
        transition={
            "run_id":verified["run_id"],
            "sequence":row["sequence"],
            "decision_tick":tick,
            "observer":citizen,
            "dimension":dimension,
            "policy":choice["policy"],
            "candidate_history_before_choice":before,
            "selected":selected,
            "selected_outcome":{
                "status":outcome["status"],
                "reason":outcome["reason"],
                "state":outcome["state"],
                "wheat":outcome["wheat"]
            },
            "unselected_outcomes":"UNKNOWN",
            "counterfactual_reward":None,
            "optimal_action_label":None,
            "new_action_authority":False
        }
        transitions.append(transition)
        if outcome["status"]=="OBSERVED":
            key=(citizen,dimension,selected)
            previous=memory.get(key)
            change=0 if previous is None else int(previous["wheat"]!=outcome["wheat"])
            memory[key]={
                "tick":tick,"wheat":outcome["wheat"],
                "count":1 if previous is None else previous["count"]+1,
                "changes":change if previous is None else previous["changes"]+change
            }
    report={
        "schema":SCHEMA,
        "origin":"VERIFIED_REAL_FORGE_ATTENTION_JOURNAL",
        "run_id":verified["run_id"],
        "source_file_sha256":verified["journal_sha256"],
        "source_final_hash":verified["final_hash"],
        "source_finalized":True,
        "records":len(transitions),
        "learning_performed":False,
        "training_labels_inferred":False,
        "minecraft_actions_authorized":False,
        "split_unit":"RUN_ID_NOT_EVENT",
        "transitions":transitions
    }
    digest=json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False)
    report["sha256"]=hashlib.sha256(digest.encode()).hexdigest()
    return report

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("journal",type=Path)
    cli.add_argument("manifest",type=Path)
    cli.add_argument("--min-records",type=int,default=1)
    cli.add_argument("--output",type=Path,default=Path("real-citizen-experience.json"))
    args=cli.parse_args()
    result=export(args.journal,args.manifest,args.min_records)
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("VERIFIED_CITIZEN_EXPERIENCE records="+str(result["records"])
          +" origin=REAL_FORGE learning=false unselected=UNKNOWN")

if __name__=="__main__":
    main()
