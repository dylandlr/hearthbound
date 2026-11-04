#!/usr/bin/env python3
"""Aggregate independently recorded, configured-seed matched Forge experiments.

An across-run description is not a causal estimate: identical chest layout
and schedule-generation logic are shared across seeds; the logged environment
is operator-controlled, not naturalistic. No event-level pseudoreplication.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

SCHEMA="hearthbound.multiseed-live-attention.v1"
INPUT="hearthbound.matched-live-forge-attention.v1"

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def aggregate(reports):
    if len(reports)<3:
        raise ValueError("At least three matched configured-seed experiments required")
    seeds=set()
    run_ids=set()
    pairs=[]
    for item in reports:
        if not isinstance(item,dict):
            raise ValueError("Invalid matched report")
        digest=item.get("sha256")
        unsigned={k:v for k,v in item.items() if k!="sha256"}
        if not isinstance(digest,str) or hashlib.sha256(canonical(unsigned).encode()).hexdigest()!=digest:
            raise ValueError("Invalid matched report digest")
        if (item.get("schema")!=INPUT
            or item.get("origin")!="ACTUAL_FINALIZED_FORGE_EXPERIMENT"
            or item.get("same_seed_matched_fixture") is not True
            or item.get("independent_world_sample") is not False
            or item.get("randomized_treatment_effect_claimed") is not False
            or item.get("counterfactual_rewards_inferred") is not False
            or item.get("learning_generalization_claimed") is not False):
            raise ValueError("Incompatible interpretation or provenance")
        seed=item.get("configured_world_seed")
        scripted=item.get("scripted_run_id")
        neural=item.get("neural_run_id")
        schedule=item.get("schedule_sha256")
        if (not isinstance(seed,str) or not seed or seed in seeds
            or not isinstance(scripted,str) or not scripted
            or not isinstance(neural,str) or not neural or scripted==neural
            or scripted in run_ids or neural in run_ids
            or not isinstance(schedule,str) or len(schedule)!=64):
            raise ValueError("Duplicate experiment or missing provenance")
        for key in ("scripted_witnessed_interventions","neural_witnessed_interventions",
                    "verified_neural_selected_inspections"):
            if type(item.get(key))!=int or item[key]<0:
                raise ValueError("Invalid recorded count")
        if (item["scripted_witnessed_interventions"]>6 or
            item["neural_witnessed_interventions"]>6 or
            item["verified_neural_selected_inspections"]<1):
            raise ValueError("Invalid observation coverage")
        for key,count in (("scripted_coverage_rate",item["scripted_witnessed_interventions"]),
                          ("neural_coverage_rate",item["neural_witnessed_interventions"])):
            if type(item.get(key)) not in (float,int) or item[key]!=round(count/6,6):
                raise ValueError("Invalid coverage rate")
        if item.get("descriptive_coverage_difference")!=round(
                item["neural_coverage_rate"]-item["scripted_coverage_rate"],6):
            raise ValueError("Invalid paired rate difference")
        seeds.add(seed)
        run_ids.update((scripted,neural))
        pairs.append({
            "configured_world_seed":seed,
            "schedule_sha256":schedule,
            "scripted_run_id":scripted,
            "neural_run_id":neural,
            "scripted_observed_of_six":item["scripted_witnessed_interventions"],
            "neural_observed_of_six":item["neural_witnessed_interventions"],
            "verified_neural_selected_inspections":item["verified_neural_selected_inspections"],
            "descriptive_coverage_difference":item["descriptive_coverage_difference"]
        })
    pairs.sort(key=lambda x:x["configured_world_seed"])
    deltas=[p["descriptive_coverage_difference"] for p in pairs]
    scripted=[p["scripted_observed_of_six"]/6 for p in pairs]
    neural=[p["neural_observed_of_six"]/6 for p in pairs]
    output={
        "schema":SCHEMA,
        "origin":"FINALIZED_REAL_FORGE_MATCHED_CONFIGURED_SEED_RUNS",
        "unit_of_analysis":"MATCHED_CONFIGURED_SEED_PAIR",
        "configured_seed_pairs":len(pairs),
        "total_real_server_runs":len(run_ids),
        "shared_chest_geometry":True,
        "world_diversity_independently_validated":False,
        "source_dynamics_naturalistic":False,
        "counterfactual_rewards_inferred":False,
        "randomized_treatment_effect_claimed":False,
        "statistical_significance_claimed":False,
        "neural_learning_in_minecraft_claimed":False,
        "generalization_claim_allowed":False,
        "scripted_unweighted_mean_coverage":round(statistics.mean(scripted),6),
        "neural_unweighted_mean_coverage":round(statistics.mean(neural),6),
        "unweighted_mean_paired_difference":round(statistics.mean(deltas),6),
        "min_paired_difference":min(deltas),
        "max_paired_difference":max(deltas),
        "all_arms_at_ceiling":all(x["scripted_observed_of_six"]==6
                                  and x["neural_observed_of_six"]==6 for x in pairs),
        "pairs":pairs,
        "interpretation":"Descriptive matched-run coverage under shared synthetic chest fixture; not evidence of generalization."
    }
    output["sha256"]=hashlib.sha256(canonical(output).encode()).hexdigest()
    return output

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("reports",nargs="+",type=Path)
    cli.add_argument("--output",type=Path,default=Path("multi-seed-live-attention-summary.json"))
    args=cli.parse_args()
    result=aggregate([json.loads(path.read_text()) for path in args.reports])
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("MULTI_SEED_LIVE_ATTENTION_FORGE pairs="+str(result["configured_seed_pairs"])
          +" scripted_mean="+str(result["scripted_unweighted_mean_coverage"])
          +" neural_mean="+str(result["neural_unweighted_mean_coverage"])
          +" ceiling="+str(result["all_arms_at_ceiling"])
          +" causal_superiority_unverified=true")

if __name__=="__main__":
    main()
