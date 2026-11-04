#!/usr/bin/env python3
"""Aggregate read-only attention shadow evidence by complete Minecraft run.

Run identity and world independence are distinct concepts: two unique UUIDs
on the same seed/fixture are NOT independent evidence of generalization.
This report only describes policy agreement with the recorded scheduler.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

SCHEMA="hearthbound.attention-run-level-shadow.v1"
INPUT="hearthbound.real-attention-shadow-comparison.v1"
POLICIES=("simulator_trained_mlp","unknown_first_then_oldest","first_registered")

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def load_report(path):
    value=json.loads(path.read_text())
    if not isinstance(value,dict):
        raise ValueError("invalid report")
    digest=value.get("sha256")
    unsigned={k:v for k,v in value.items() if k!="sha256"}
    if not isinstance(digest,str) or hashlib.sha256(canonical(unsigned).encode()).hexdigest()!=digest:
        raise ValueError("invalid source report digest")
    if (value.get("schema")!=INPUT or value.get("origin")!="REAL_FORGE_OFFLINE_SHADOW"
        or value.get("reward_comparison_performed") is not False
        or value.get("counterfactual_outcomes_inferred") is not False
        or value.get("minecraft_actions_authorized") is not False
        or value.get("policy_training_origin")!="SIMULATED_ONLY"):
        raise ValueError("source report violates evidence contract")
    count=value.get("real_decisions")
    if type(count)!=int or count<1:
        raise ValueError("empty decision report")
    policies=value.get("policies")
    if not isinstance(policies,dict) or set(policies)!=set(POLICIES):
        raise ValueError("wrong policy comparison")
    for name in POLICIES:
        row=policies[name]
        a=row.get("agreements")
        d=row.get("disagreements")
        u=row.get("unknown_alternative_outcomes")
        known=row.get("known_selected_outcomes")
        recommendations=row.get("recommendations")
        if (any(type(x)!=int or x<0 for x in (a,d,u,known))
            or a+d!=count or u!=d or known>a
            or not isinstance(recommendations,list) or len(recommendations)!=count
            or row.get("agreement_rate")!=round(a/count,6)):
            raise ValueError("invalid policy-level accounting")
        for recommendation in recommendations:
            if (type(recommendation.get("agreed"))!=bool
                or recommendation.get("outcome_evaluable") not in (True,False)
                or (recommendation["outcome_evaluable"] and not recommendation["agreed"])
                or recommendation.get("alternative_outcome")!=(
                    "NOT_APPLICABLE" if recommendation["agreed"] else "UNKNOWN")):
                raise ValueError("counterfactual or invalid recommendation")
        if sum(int(x["agreed"]) for x in recommendations)!=a:
            raise ValueError("recommendation totals mismatch")
        if sum(int(x["outcome_evaluable"]) for x in recommendations)!=known:
            raise ValueError("known outcome totals mismatch")
    return value

def aggregate(paths):
    if not paths:
        raise ValueError("at least one shadow report required")
    reports=[load_report(Path(p)) for p in paths]
    ids=[x.get("run_id") for x in reports]
    if any(not isinstance(x,str) or not x for x in ids) or len(set(ids))!=len(ids):
        raise ValueError("run IDs missing or duplicate")
    runs=[]
    for x in sorted(reports,key=lambda r:r["run_id"]):
        policy_results={}
        for name in POLICIES:
            v=x["policies"][name]
            policy_results[name]={
                "decisions":x["real_decisions"],
                "agreement_rate":v["agreement_rate"],
                "agreements":v["agreements"],
                "unknown_alternative_outcomes":v["unknown_alternative_outcomes"],
                "known_selected_outcomes":v["known_selected_outcomes"]
            }
        runs.append({"run_id":x["run_id"],
                     "real_decisions":x["real_decisions"],
                     "source_file_sha256":x.get("source_file_sha256"),
                     "input_experience_sha256":x.get("input_experience_sha256"),
                     "policies":policy_results})
    aggregate_policies={}
    for name in POLICIES:
        rates=[r["policies"][name]["agreement_rate"] for r in runs]
        aggregate_policies[name]={
            "run_count":len(runs),
            "unweighted_mean_run_agreement_rate":round(statistics.mean(rates),6),
            "min_run_agreement_rate":min(rates),
            "max_run_agreement_rate":max(rates),
            "total_agreements_descriptive_only":sum(r["policies"][name]["agreements"] for r in runs),
            "total_unknown_alternatives":sum(r["policies"][name]["unknown_alternative_outcomes"] for r in runs)
        }
    output={
        "schema":SCHEMA,
        "origin":"VERIFIED_REAL_FORGE_SHADOW_SUMMARIES",
        "unit_of_analysis":"RUN",
        "independence_verified":False,
        "world_seed_provenance_available":False,
        "generalization_claim_allowed":False,
        "statistical_significance_claimed":False,
        "reward_comparison_performed":False,
        "minecraft_actions_authorized":False,
        "distinct_run_ids":len(runs),
        "runs":runs,
        "policies":aggregate_policies,
        "interpretation":"Agreement with a scripted scheduler, not policy quality; unique run IDs do not establish independent world seeds."
    }
    output["sha256"]=hashlib.sha256(canonical(output).encode()).hexdigest()
    return output

def main():
    p=argparse.ArgumentParser()
    p.add_argument("reports",nargs="+",type=Path)
    p.add_argument("--output",type=Path,default=Path("real-attention-run-level-analysis.json"))
    args=p.parse_args()
    result=aggregate(args.reports)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    for name,row in result["policies"].items():
        print("ATTENTION_RUN_LEVEL",name,
              "mean_agreement="+str(row["unweighted_mean_run_agreement_rate"]),
              "runs="+str(row["run_count"]))
    print("RUN_LEVEL_SHADOW_COMPLETE independence_unverified=true rewards=false")

if __name__=="__main__":
    main()
