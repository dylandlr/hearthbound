#!/usr/bin/env python3
"""Aggregate physical Minecraft trial receipts, never invented counterfactuals.

Matched-world pilots are descriptive. Bootstrap intervals from only two seeds
are diagnostic, NOT proof of trained-policy superiority. One world per arm.
"""
import argparse
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

SCHEMA="hearthbound.matched-real-physical-haul.v1"
REPORT_SCHEMA="hearthbound.matched-physical-policy-comparison.v1"
POLICIES=("SCRIPTED","FROZEN_MLP")

def validate(x):
    if x.get("schema")!=SCHEMA or x.get("evidence_origin")!="REAL_FORGE_WORLD_INVENTORY":
        raise ValueError("Not a physical Forge trial receipt")
    if x.get("policy") not in POLICIES or x.get("scenario") not in (
            "fresh","unannounced_depletion"):
        raise ValueError("Invalid treatment or scenario")
    if type(x.get("seed")) is not int or x["seed"]<=0:
        raise ValueError("Invalid matched world seed")
    if not isinstance(x.get("model_sha256"),str) or len(x["model_sha256"])!=64:
        raise ValueError("Missing frozen model identity")
    for name in ("operator_triggered","scout_distinct_from_executor",
                 "training_includes_this_world","no_model_updates",
                 "research_reward_authorized","technology_unlocked"):
        actual=x.get(name)
        wanted=(name in ("operator_triggered","scout_distinct_from_executor",
                         "no_model_updates"))
        if actual is not wanted:
            raise ValueError("Trial provenance or reward scope violated: "+name)
    for name in ("before","after"):
        v=x.get(name)
        if not isinstance(v,dict) or set(v)!={"A","B","destination"} or any(
                type(v[k]) is not int or v[k]<0 for k in v):
            raise ValueError("Unverifiable endpoint inventories")
    if x.get("status") not in (
            "EXECUTOR_COMPLETED","PAUSED_OR_QUARANTINED","TIMEOUT","ABSTAIN"):
        raise ValueError("Unrecognized real motor status")
    selected=x.get("selected")
    if selected not in ("A","B","NONE"):
        raise ValueError("Unrecognized model selection")
    if x.get("status")=="ABSTAIN":
        if selected!="NONE" or "job" in x or x["before"]!=x["after"]:
            raise ValueError("Abstention changed physical world or assigned job")
        if x.get("physical_success") is not False or x.get("utility")!=0.0:
            raise ValueError("Invented abstention reward")
    else:
        if selected not in ("A","B") or not isinstance(x.get("job"),str):
            raise ValueError("Missing executor job for attempted work")
        success=(x.get("status")=="EXECUTOR_COMPLETED"
            and x["before"][selected]>0
            and x["after"][selected]==x["before"][selected]-1
            and x["after"]["destination"]==x["before"]["destination"]+1
            and x["after"]["B" if selected=="A" else "A"]==
                x["before"]["B" if selected=="A" else "A"])
        if x.get("physical_success") is not success:
            raise ValueError("Claimed physical outcome lacks chest-delta evidence")
        if x.get("inventory_delta_verified") is not success:
            raise ValueError("Inventory verification claim disagrees with physical receipt")
        if x.get("utility")!=(1.0 if success else -0.5):
            raise ValueError("Unregistered utility after outcome")
        if success and "status=EXECUTOR_COMPLETED" not in x.get("completion_receipt",""):
            raise ValueError("No authoritative Minecraft executor completion evidence")
    if x.get("completed_item_count")!=int(x.get("physical_success",False)):
        raise ValueError("Claimed item throughput without physical evidence")
    if x.get("chest_counts_independently_read") is not True:
        raise ValueError("Invented inventory oracle")
    if x.get("model_updated") is True or x.get("rewards_issued") is True:
        raise ValueError("Training or reward side effect inside pilot")
    return x

def summarize(receipts):
    paired=defaultdict(dict)
    frozen=set()
    for x in receipts:
        validate(x)
        frozen.add(x["model_sha256"])
        key=(x["seed"],x["scenario"])
        if x["policy"] in paired[key]:
            raise ValueError("Duplicate policy trial for same matched seed")
        paired[key][x["policy"]]=x
    if len(frozen)!=1:
        raise ValueError("Different frozen model checksum between arms")
    if len(paired)<2:
        raise ValueError("At least two independent matched seeds required")
    if any(set(value)!=set(POLICIES) for value in paired.values()):
        raise ValueError("Missing policy arm for matched real Minecraft world")
    if len({seed for seed,scenario in paired})!=len(paired):
        raise ValueError("One scenario per world seed for this pilot")
    keys=sorted(paired)
    rows=[]
    for seed,scenario in keys:
        t=paired[(seed,scenario)]
        for p in POLICIES:
            x=t[p]
            rows.append({"seed":seed,"scenario":scenario,"policy":p,
                "status":x["status"],"selected":x["selected"],
                "utility":x["utility"],
                "items_delivered":x["completed_item_count"],
                "server_ticks":x.get("completed_server_ticks",0)})
    policy_summary={}
    for p in POLICIES:
        trial=[paired[k][p] for k in keys]
        success=[x for x in trial if x["physical_success"]]
        policy_summary[p]={
            "trials":len(trial),
            "completed_items":sum(x["completed_item_count"] for x in trial),
            "success_rate":sum(x["physical_success"] for x in trial)/len(trial),
            "abstain_rate":sum(x["status"]=="ABSTAIN" for x in trial)/len(trial),
            "failed_assignment_rate":sum(
                x["status"] in ("PAUSED_OR_QUARANTINED","TIMEOUT")
                for x in trial)/len(trial),
            "mean_utility":round(sum(x["utility"] for x in trial)/len(trial),5),
            "mean_completion_ticks_success_only":(
                round(sum(x["completed_server_ticks"] for x in success)/len(success),2)
                if success else None),
        }
    diffs=[paired[k]["FROZEN_MLP"]["utility"]
          -paired[k]["SCRIPTED"]["utility"] for k in keys]
    paired_delta=sum(diffs)/len(diffs)
    # Cluster bootstrap resamples *paired seeds*, never individual policies.
    rng=random.Random(20261108)
    boot=[sum(rng.choice(diffs) for _ in diffs)/len(diffs) for _ in range(4000)]
    boot.sort()
    low=boot[int(0.025*len(boot))]
    high=boot[int(0.975*len(boot))-1]
    digest=hashlib.sha256(json.dumps(
        rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return {
        "schema":REPORT_SCHEMA,
        "real_minecraft_observations_only":True,
        "paired_world_count":len(keys),
        "physical_trial_count":len(receipts),
        "model_sha256":next(iter(frozen)),
        "registered_utility":"item_delivered=+1,failed_assignment=-0.5,abstain=0",
        "sample_too_small_to_claim_superiority":len(keys)<20,
        "model_superiority_claimed":False,
        "oracle":"chest_source_delta=-1 and chest_destination_delta=+1 AND executor_NBT_completed",
        "scripted_and_mlp_same_executor_motor":True,
        "policy":policy_summary,
        "frozen_minus_scripted_mean_utility":round(paired_delta,5),
        "paired_seed_bootstrap_ci95_descriptive":[round(low,5),round(high,5)],
        "bootstrap_samples":len(boot),
        "trial_rows":rows,
        "evidence_sha256":digest,
        "limitation":"Pilot uses small matched worlds; no inference of learned collaboration or robust productivity superiority",
        "research_reward_authorized":False,"model_updates_during_forge":False,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("receipts",type=Path,nargs="+")
    ap.add_argument("--out",type=Path,required=True)
    args=ap.parse_args()
    data=[json.loads(path.read_text()) for path in args.receipts]
    result=summarize(data)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("REAL_FORGE_MATCHED_PHYSICAL_COMPARISON_PASS",
          json.dumps({k:result[k] for k in (
              "paired_world_count","physical_trial_count",
              "frozen_minus_scripted_mean_utility",
              "paired_seed_bootstrap_ci95_descriptive",
              "sample_too_small_to_claim_superiority")},sort_keys=True))

if __name__=="__main__":
    main()
