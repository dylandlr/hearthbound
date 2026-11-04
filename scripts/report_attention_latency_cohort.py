#!/usr/bin/env python3
"""Run-level summary of real Forge witness timing across configured seeds."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path
from report_matched_attention_latency import canonical,SCHEMA as PAIR_SCHEMA

SCHEMA="hearthbound.forge-attention-latency-cohort.v1"

def cohort(rows):
    if len(rows)<3:raise ValueError("three configured seeds required")
    seeds=set()
    run_ids=set()
    summaries=[]
    for row in rows:
        digest=row.get("sha256")
        body={k:v for k,v in row.items() if k!="sha256"}
        if (row.get("schema")!=PAIR_SCHEMA
            or row.get("origin")!="REAL_FORGE_VERIFIED_SELECTED_SOURCE_OBSERVATIONS"
            or row.get("identical_stimulus_timing_verified") is not False
            or row.get("independent_world_conditions_verified") is not False
            or row.get("causal_latency_advantage_claimed") is not False
            or row.get("unselected_counterfactual_outcomes_inferred") is not False
            or not isinstance(digest,str)
            or hashlib.sha256(canonical(body).encode()).hexdigest()!=digest):
            raise ValueError("invalid signed latency provenance")
        seed=row.get("configured_world_seed")
        a=row.get("scripted_run_id")
        b=row.get("neural_run_id")
        if (not isinstance(seed,str) or not seed or seed in seeds
            or not isinstance(a,str) or not a or a==b
            or not isinstance(b,str) or not b or a in run_ids or b in run_ids):
            raise ValueError("duplicate run or seed")
        if (not isinstance(row.get("per_intervention"),list)
            or len(row["per_intervention"])!=6
            or any(type(r.get("index"))!=int or r["index"]!=i
                   or r.get("server_tick_trajectories_identical") is not False
                   for i,r in enumerate(row["per_intervention"],1))):
            raise ValueError("invalid intervention details")
        compared=sum(x["both_witnessed"] is True for x in row["per_intervention"])
        if compared!=row.get("both_witnessed_events"):
            raise ValueError("incorrect shared observation count")
        delays=[x["descriptive_neural_minus_scripted_ticks"] for x in row["per_intervention"]
                if x["both_witnessed"]]
        if (any(type(x) not in (int,float) for x in delays)
            or (round(statistics.mean(delays),4) if delays else None)
                !=row.get("mean_descriptive_neural_minus_scripted_latency_ticks")):
            raise ValueError("inconsistent latency difference")
        seeds.add(seed);run_ids.update((a,b))
        summaries.append({
            "configured_world_seed":seed,
            "scripted_run_id":a,
            "neural_run_id":b,
            "both_witnessed_events":compared,
            "mean_descriptive_neural_minus_scripted_ticks":
                row["mean_descriptive_neural_minus_scripted_latency_ticks"],
            "scripted_mean_observed_latency_ticks":
                row["scripted"]["mean_observed_first_witness_latency_ticks"],
            "neural_mean_observed_latency_ticks":
                row["neural"]["mean_observed_first_witness_latency_ticks"]
        })
    summaries.sort(key=lambda x:x["configured_world_seed"])
    comparable=[x["mean_descriptive_neural_minus_scripted_ticks"] for x in summaries
                if x["mean_descriptive_neural_minus_scripted_ticks"] is not None]
    result={
        "schema":SCHEMA,
        "origin":"MATCHED_REAL_FORGE_LATENCY_RUN_SUMMARIES",
        "configured_seed_pairs":len(rows),
        "real_server_runs":len(run_ids),
        "unit_of_analysis":"CONFIGURED_SEED_PAIR",
        "pairs_with_shared_witnesses":len(comparable),
        "unweighted_mean_of_pair_differences_ticks":
            round(statistics.mean(comparable),4) if comparable else None,
        "resource_fixture_variety_verified":False,
        "identical_intervention_tick_alignment_verified":False,
        "significance_claimed":False,
        "neural_superiority_claimed":False,
        "neural_learning_in_minecraft_claimed":False,
        "pairs":summaries
    }
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("reports",type=Path,nargs="+")
    p.add_argument("--output",type=Path,default=Path("forge-attention-latency-cohort.json"))
    args=p.parse_args()
    result=cohort([json.loads(path.read_text()) for path in args.reports])
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("FORGE_ATTENTION_LATENCY_COHORT runs="+str(result["real_server_runs"])
          +" descriptive_mean_ticks="+str(result["unweighted_mean_of_pair_differences_ticks"])
          +" neural_superiority_unverified=true")

if __name__=="__main__":
    main()
