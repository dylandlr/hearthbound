#!/usr/bin/env python3
"""Audited separation between probability forecast quality and policy utility."""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

REGIMES=("in_distribution","low_volatility","unequal_volatility","high_volatility")
RATES=(1,2,4)
SCHEMA="hearthbound.observed-change-forecast-admission.v1"
def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def audit(source):
    unsigned={k:v for k,v in source.items() if k!="sha256"}
    if (source.get("schema")!="hearthbound.observed-change-forecast.v1"
        or source.get("origin")!="SIMULATED_ONLY"
        or source.get("sha256")!=hashlib.sha256(canonical(unsigned).encode()).hexdigest()
        or source.get("model_deployed_in_minecraft") is not False
        or source.get("minecraft_model_promotion_authorized") is not False
        or source.get("unselected_rewards_or_labels_used") is not False
        or source.get("all_policy_evaluations_use_frozen_timelines") is not True
        or source.get("first_inspections_masked_from_training_and_forecast_metrics") is not True):
        raise ValueError("invalid or unauthorized forecast evidence")
    seeds=source.get("seeds")
    cases=source.get("cases")
    if (not isinstance(seeds,list) or len(seeds)<3 or len(set(seeds))!=len(seeds)
        or not isinstance(cases,list) or len(cases)!=len(seeds)*12):
        raise ValueError("incomplete training and heldout evaluation matrix")
    seen=set()
    by_seed={s:[] for s in seeds}
    by_regime={r:[] for r in REGIMES}
    brier_delta=[]
    policy_delta=[]
    for cell in cases:
        seed=cell.get("training_seed")
        regime=cell.get("regime")
        rate=cell.get("world_updates_per_inspection")
        key=(seed,regime,rate)
        if (seed not in by_seed or regime not in by_regime
            or rate not in RATES or key in seen
            or cell.get("heldout_episodes")!=source.get("heldout_episodes_per_cell")):
            raise ValueError("missing or duplicate evaluation cell")
        seen.add(key)
        forecasts=cell.get("forecast")
        n=forecasts.get("evaluated_reinspection_labels")
        bins=forecasts.get("calibration_bins")
        if (type(n)!=int or n<1 or not isinstance(bins,list) or len(bins)!=5
            or sum(item.get("count",0) for item in bins)!=n):
            raise ValueError("missing directly witnessed calibration labels")
        for idx,item in enumerate(bins):
            if item.get("probability_bin")!=idx:
                raise ValueError("invalid calibration bin")
            for name in ("mean_confidence","observed_change_fraction"):
                value=item.get(name)
                if (value is not None and
                    (type(value) not in (float,int) or not 0<=value<=1)):
                    raise ValueError("invalid calibration value")
        b=forecasts.get("gru_brier")
        historical=forecasts.get("observed_history_baseline_brier")
        scores=cell.get("mean_direct_discoveries")
        delta=cell.get("forecast_policy_minus_scripted")
        if (any(type(v) not in (float,int) or not math.isfinite(v)
                or not 0<=v<=1 for v in (b,historical))
            or not isinstance(scores,dict)
            or set(scores)!={"scripted","forecast_gated"}
            or any(type(v) not in (float,int) or not 0<=v<=32
                   for v in scores.values())
            or type(delta) not in (float,int)
            or abs(round(scores["forecast_gated"]-scores["scripted"],6)-delta)>0.000002):
            raise ValueError("unsupported direct-discovery or Brier result")
        brier_delta.append(historical-b)
        policy_delta.append(delta)
        by_seed[seed].append(delta)
        by_regime[regime].append(delta)
    per_seed=[{"seed":s,"mean_policy_minus_scripted":round(statistics.mean(x),6)}
              for s,x in sorted(by_seed.items())]
    per_regime=[{"regime":r,"mean_policy_minus_scripted":round(statistics.mean(by_regime[r]),6)}
                for r in REGIMES]
    prediction_better=statistics.mean(brier_delta)>0
    policy_better_all_seeds=all(x["mean_policy_minus_scripted"]>=0 for x in per_seed)
    policy_robust=all(x["mean_policy_minus_scripted"]>=-.25 for x in per_regime)
    result={
        "schema":SCHEMA,"origin":"VERIFIED_SIMULATOR_ONLY",
        "cases_checked":len(cases),"training_seeds":seeds,
        "mean_brier_improvement_vs_history":round(statistics.mean(brier_delta),6),
        "prediction_better_than_history_on_average":prediction_better,
        "mean_policy_discovery_difference":round(statistics.mean(policy_delta),6),
        "per_seed":per_seed,"per_regime":per_regime,
        "policy_nonnegative_in_every_training_seed":policy_better_all_seeds,
        "policy_regime_robustness":policy_robust,
        "candidate_passed_joint_simulator_admission":(
            prediction_better and policy_better_all_seeds and policy_robust),
        "real_forge_advantage_established":False,
        "statistical_significance_established":False,
        "minecraft_model_promotion_authorized":False}
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,default=Path("observed-change-admission.json"))
    args=parser.parse_args()
    result=audit(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("FORECAST_AND_POLICY_ADMISSION admitted="+
          str(result["candidate_passed_joint_simulator_admission"]).lower()+
          " forge_promotion=false")

if __name__=="__main__":
    main()
