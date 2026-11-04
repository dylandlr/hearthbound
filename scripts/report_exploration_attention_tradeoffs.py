#!/usr/bin/env python3
"""Audit held-out synthetic exploration trade-offs across training seeds.

Never authorize promotion from this analysis. Separate simulator learning
from any future independently validated real Forge evaluation.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

SCHEMA="hearthbound.exploration-attention-tradeoffs.v1"
INPUT="hearthbound.exploration-aware-attention.v1"
ARMS=("legacy_style","mixed_rapid_curriculum","exploration_aware")
REGIMES=("in_distribution","low_volatility","unequal_volatility","high_volatility")
RATES=(1,2,4)

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def summarize(report):
    digest=report.get("sha256")
    payload={k:v for k,v in report.items() if k!="sha256"}
    if (report.get("schema")!=INPUT or report.get("origin")!="SIMULATED_ONLY"
        or not isinstance(digest,str)
        or hashlib.sha256(canonical(payload).encode()).hexdigest()!=digest
        or report.get("minecraft_model_deployed") is not False
        or report.get("model_promotion_authorized") is not False
        or report.get("real_minecraft_journals_used_for_training") is not False
        or report.get("only_selected_source_rewards_available_to_training") is not True
        or report.get("hidden_truth_visible_to_policy") is not False
        or report.get("true_volatility_visible_to_policy") is not False):
        raise ValueError("unsafe or altered synthetic training evidence")
    seeds=report.get("training_seeds")
    if (not isinstance(seeds,list) or len(seeds)<3
        or len(set(seeds))!=len(seeds)
        or any(type(v)!=int or v<0 for v in seeds)):
        raise ValueError("insufficient distinct training seeds")
    cases=report.get("cases")
    if not isinstance(cases,list) or len(cases)!=len(seeds)*len(REGIMES)*len(RATES):
        raise ValueError("incomplete benchmark matrix")
    all_keys=set()
    grouped={(regime,arm):[] for regime in REGIMES for arm in ARMS}
    overall={arm:[] for arm in ARMS}
    for item in cases:
        seed=item.get("training_seed")
        regime=item.get("regime")
        rate=item.get("hidden_updates_per_inspection")
        key=(seed,regime,rate)
        if (seed not in seeds or regime not in REGIMES or rate not in RATES
            or key in all_keys or item.get("heldout_episodes")!=
                report.get("heldout_episodes_per_seed_regime_rate")):
            raise ValueError("duplicate or mismatched held-out case")
        all_keys.add(key)
        expected=item.get("differences")
        results=item.get("summaries")
        if not isinstance(expected,dict) or set(expected)!=set(ARMS):
            raise ValueError("missing policy differences")
        if not isinstance(results,dict) or set(results)!={"scripted",*ARMS}:
            raise ValueError("missing policy observations")
        for arm in ARMS:
            value=expected[arm].get("mean_neural_minus_scripted_discoveries")
            if type(value) not in (float,int) or not -32<=value<=32:
                raise ValueError("invalid discovery delta")
            counts=[expected[arm].get(name) for name in (
                "episodes_better_than_scripted",
                "episodes_worse_than_scripted",
                "episodes_tied_with_scripted")]
            if (any(type(c)!=int or c<0 for c in counts)
                or sum(counts)!=item["heldout_episodes"]):
                raise ValueError("invalid matched episode accounting")
            scripted=results["scripted"].get("mean_direct_discoveries")
            measured=results[arm].get("mean_direct_discoveries")
            if (type(scripted) not in (float,int)
                or type(measured) not in (float,int)
                or abs(round(measured-scripted,5)-value)>0.00002):
                raise ValueError("delta disagrees with actual direct discoveries")
            grouped[(regime,arm)].append(value)
            overall[arm].append(value)
    if len(all_keys)!=len(cases):raise ValueError("missing matrix cases")
    regimes=[]
    for regime in REGIMES:
        entry={"regime":regime}
        for arm in ARMS:
            values=grouped[(regime,arm)]
            entry[arm]={
                "mean_neural_minus_scripted_discoveries":round(statistics.mean(values),5),
                "worst_seed_rate_delta":min(values),
                "best_seed_rate_delta":max(values),
                "positive_seed_rate_cases":sum(x>0 for x in values),
                "negative_seed_rate_cases":sum(x<0 for x in values)}
        regimes.append(entry)
    output={
        "schema":SCHEMA,"origin":"SIMULATED_ONLY_VERIFIED_THREE_SEED_MATRIX",
        "training_seeds":seeds,
        "heldout_regimes":list(REGIMES),
        "heldout_update_rates":list(RATES),
        "total_evaluation_cases":len(cases),
        "comparison_unit":"TRAINING_SEED_REGIME_RATE",
        "aggregate":{
            arm:{"mean_neural_minus_scripted_discoveries":
                    round(statistics.mean(overall[arm]),5),
                 "worst_case_delta":min(overall[arm]),
                 "negative_cases":sum(x<0 for x in overall[arm])}
            for arm in ARMS},
        "regimes":regimes,
        "model_promotion_authorized":False,
        "real_forge_outcomes_used":False,
        "statistical_significance_claimed":False,
        "generalization_to_minecraft_claimed":False,
        "interpretation":"Exploratory simulator trade-offs only; no live model promotion."
    }
    output["sha256"]=hashlib.sha256(canonical(output).encode()).hexdigest()
    return output

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("input",type=Path)
    cli.add_argument("--output",type=Path,default=Path("exploration-tradeoffs.json"))
    args=cli.parse_args()
    summary=summarize(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(summary,sort_keys=True,indent=2)+"\n")
    print("EXPLORATION_TRADEOFF_AUDIT regimes="+str(len(summary["regimes"]))+
          " promotion=false real_forge=false")

if __name__=="__main__":
    main()
