#!/usr/bin/env python3
"""Audits frozen-forecaster attention utility without licensing deployment."""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

SCHEMA="hearthbound.forecast-policy-admission.v1"
REGIMES=("in_distribution","low_volatility","unequal_volatility","high_volatility")
RATES=(1,2,4)
ARMS=("scripted","greedy_forecast","age_blend","coverage_guard")
def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def audit(report):
    raw={k:v for k,v in report.items() if k!="sha256"}
    if (report.get("schema")!="hearthbound.forecast-policy-gating.v1"
        or report.get("origin")!="SIMULATED_ONLY"
        or report.get("sha256")!=hashlib.sha256(canonical(raw).encode()).hexdigest()
        or report.get("same_frozen_forecaster_for_every_policy_per_seed") is not True
        or report.get("frozen_trajectories_shared_between_policies") is not True
        or report.get("policy_can_access_unselected_source_truth") is not False
        or report.get("minecraft_model_promotion_authorized") is not False):
        raise ValueError("invalid frozen forecaster provenance")
    seeds=report.get("training_seeds")
    cases=report.get("cases")
    digests=report.get("model_hashes_by_training_seed")
    if (not isinstance(seeds,list) or len(seeds)<3
        or len(set(seeds))!=len(seeds) or any(type(s)!=int for s in seeds)
        or not isinstance(cases,list) or len(cases)!=len(seeds)*12
        or not isinstance(digests,dict) or set(digests)!={str(s) for s in seeds}):
        raise ValueError("missing independent seed evidence")
    seen=set()
    by_arm={a:[] for a in ARMS[1:]}
    by_seed={a:{s:[] for s in seeds} for a in ARMS[1:]}
    by_regime={a:{r:[] for r in REGIMES} for a in ARMS[1:]}
    deviations={a:[] for a in ARMS[1:]}
    for row in cases:
        s=row.get("training_seed")
        regime=row.get("regime")
        rate=row.get("updates_per_inspection")
        key=(s,regime,rate)
        if (s not in seeds or regime not in REGIMES or rate not in RATES
            or key in seen or row.get("heldout_episodes")!=
                report.get("heldout_episodes_per_cell")
            or row.get("frozen_model_sha256")!=digests.get(str(s))):
            raise ValueError("duplicate or mismatched policy trial")
        seen.add(key)
        scores=row.get("mean_direct_discoveries")
        differences=row.get("mean_vs_scripted")
        policy_deviations=row.get("mean_policy_deviations_from_scripted")
        if (not isinstance(scores,dict) or set(scores)!=set(ARMS)
            or not isinstance(differences,dict) or set(differences)!=set(ARMS[1:])
            or not isinstance(policy_deviations,dict) or
                set(policy_deviations)!=set(ARMS)):
            raise ValueError("missing policy observations")
        if (any(type(x) not in (int,float) or not math.isfinite(x)
                or not 0<=x<=32 for x in scores.values())
            or policy_deviations["scripted"]!=0):
            raise ValueError("impossible selected observation count")
        for arm in ARMS[1:]:
            delta=differences[arm]
            dev=policy_deviations[arm]
            if (type(delta) not in (int,float)
                or not math.isfinite(delta)
                or abs(round(scores[arm]-scores["scripted"],6)-delta)>0.000002
                or type(dev) not in (int,float) or not 0<=dev<=32):
                raise ValueError("unverified selected decisions")
            by_arm[arm].append(delta)
            by_seed[arm][s].append(delta)
            by_regime[arm][regime].append(delta)
            deviations[arm].append(dev)
    decisions={}
    for arm in ARMS[1:]:
        per_seed={str(s):round(statistics.mean(by_seed[arm][s]),6) for s in seeds}
        per_regime={r:round(statistics.mean(by_regime[arm][r]),6) for r in REGIMES}
        active=any(v>0 for v in deviations[arm])
        seed_stable=all(v>=0 for v in per_seed.values())
        regime_stable=all(v>=0 for v in per_regime.values())
        decisions[arm]={
            "overall_delta_vs_scripted":round(statistics.mean(by_arm[arm]),6),
            "per_seed":per_seed,"per_regime":per_regime,
            "negative_cells":sum(x<0 for x in by_arm[arm]),
            "mean_policy_deviations":round(statistics.mean(deviations[arm]),6),
            "neural_policy_effectively_active":active,
            "positive_in_every_training_seed":seed_stable,
            "nonnegative_in_every_regime":regime_stable,
            "passed_exploratory_admission":active and seed_stable and regime_stable}
    result={"schema":SCHEMA,"origin":"VERIFIED_SYNTHETIC_POLICY_COMPARISON",
            "case_count":len(cases),"seed_count":len(seeds),
            "policies":decisions,
            "real_forge_generalization_established":False,
            "statistical_significance_established":False,
            "minecraft_model_promotion_authorized":False}
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("input",type=Path)
    p.add_argument("--output",type=Path,default=Path("forecast-policy-admission.json"))
    args=p.parse_args()
    out=audit(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(out,sort_keys=True,indent=2)+"\n")
    for name,item in out["policies"].items():
        print("FORECAST_POLICY_ADMISSION policy="+name+
              " active="+str(item["neural_policy_effectively_active"]).lower()+
              " admitted="+str(item["passed_exploratory_admission"]).lower())
if __name__=="__main__":
    main()
