#!/usr/bin/env python3
"""Fail-closed synthetic uncertainty-objective admission report.

Cannot authorize model promotion; counts complete training-seed and regime
robustness rather than masking failures in a pooled average.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

SCHEMA="hearthbound.observed-uncertainty-admission.v1"
INPUT="hearthbound.observed-uncertainty-objective.v1"
REGIMES=("in_distribution","low_volatility","unequal_volatility","high_volatility")
RATES=(1,2,4)
ARMS=("exploration_neural","history_gated","uncertainty_neural")

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def audit(report):
    unsigned={k:v for k,v in report.items() if k!="sha256"}
    if (report.get("schema")!=INPUT or report.get("origin")!="SIMULATED_ONLY"
        or report.get("sha256")!=hashlib.sha256(canonical(unsigned).encode()).hexdigest()
        or report.get("model_promotion_authorized") is not False
        or report.get("forge_journal_used_for_training") is not False
        or report.get("unselected_truth_or_rewards_used_for_learning") is not False
        or report.get("true_volatility_feature") is not False):
        raise ValueError("unsupported synthetic evidence provenance")
    seeds=report.get("training_seeds")
    cases=report.get("cases")
    if (not isinstance(seeds,list) or len(seeds)<3 or len(set(seeds))!=len(seeds)
        or any(type(x)!=int or x<0 for x in seeds)
        or not isinstance(cases,list) or len(cases)!=12*len(seeds)):
        raise ValueError("incomplete independent-seed comparison")
    seen=set()
    by_seed={seed:[] for seed in seeds}
    by_regime={regime:[] for regime in REGIMES}
    all_deltas=[]
    for cell in cases:
        seed=cell.get("train_seed")
        regime=cell.get("regime")
        rate=cell.get("hidden_updates_per_inspection")
        key=(seed,regime,rate)
        if (seed not in by_seed or regime not in by_regime or rate not in RATES
            or key in seen or cell.get("heldout_episodes")!=
                report.get("heldout_episodes_per_cell")):
            raise ValueError("duplicate or incomplete held-out setting")
        seen.add(key)
        diffs=cell.get("mean_neural_minus_scripted_discoveries")
        scores=cell.get("policy_scores")
        if (not isinstance(diffs,dict) or set(diffs)!=set(ARMS)
            or not isinstance(scores,dict) or set(scores)!={"scripted",*ARMS}):
            raise ValueError("missing arm outcome")
        baseline=scores["scripted"].get("mean_direct_discoveries")
        if type(baseline) not in (int,float) or not 0<=baseline<=32:
            raise ValueError("invalid scripted outcome")
        for arm in ARMS:
            outcome=scores[arm].get("mean_direct_discoveries")
            delta=diffs[arm]
            if (type(outcome) not in (int,float) or not 0<=outcome<=32
                or type(delta) not in (int,float)
                or abs(round(outcome-baseline,5)-delta)>0.00002):
                raise ValueError("outcome delta does not match direct discoveries")
        x=diffs["uncertainty_neural"]
        by_seed[seed].append(x)
        by_regime[regime].append(x)
        all_deltas.append(x)
    seed_results=[{"seed":key,"mean_neural_minus_scripted":round(statistics.mean(values),5)}
                  for key,values in sorted(by_seed.items())]
    regime_results=[{"regime":key,"mean_neural_minus_scripted":round(statistics.mean(by_regime[key]),5)}
                    for key in REGIMES]
    # These exploratory thresholds prevent a pooled average from concealing
    # regressions, but passing NEVER authorizes Minecraft deployment.
    seed_pass=all(x["mean_neural_minus_scripted"]>=0 for x in seed_results)
    regime_pass=all(x["mean_neural_minus_scripted"]>=-.25 for x in regime_results)
    result={
        "schema":SCHEMA,
        "origin":"VERIFIED_SYNTHETIC_TRAINING_SEED_AND_REGIME_AUDIT",
        "seed_results":seed_results,
        "regime_results":regime_results,
        "overall_mean_neural_minus_scripted":round(statistics.mean(all_deltas),5),
        "seed_consistency_passed":seed_pass,
        "regime_robustness_passed":regime_pass,
        "candidate_passed_simulator_admission":seed_pass and regime_pass,
        "admission_policy":"EVERY_TRAINING_SEED_NONNEGATIVE_AND_ALL_REGIMES_AT_LEAST_MINUS_0_25",
        "real_forge_generalization_established":False,
        "statistical_significance_established":False,
        "minecraft_model_promotion_authorized":False}
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("input",type=Path)
    cli.add_argument("--output",type=Path,default=Path("observed-uncertainty-admission.json"))
    args=cli.parse_args()
    result=audit(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("UNCERTAINTY_OBJECTIVE_ADMISSION simulator_pass="+
          str(result["candidate_passed_simulator_admission"]).lower()+
          " minecraft_promotion=false")
if __name__=="__main__":
    main()
