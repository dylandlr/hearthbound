#!/usr/bin/env python3
"""Conservative research admission audit for heldout history-gated MLP.

This audit can rule a candidate OUT but can never authorize live deployment.
No real Forge outcomes, unseen source truth, or counterfactual rewards involved.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

SCHEMA="hearthbound.history-gated-admission.v1"
INPUT="hearthbound.history-gated-attention.v1"
REGIMES=("in_distribution","low_volatility","unequal_volatility","high_volatility")
RATES=(1,2,4)

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def audit(report):
    digest=report.get("sha256")
    unsigned={k:v for k,v in report.items() if k!="sha256"}
    if (report.get("schema")!=INPUT or report.get("origin")!="SIMULATED_ONLY"
        or not isinstance(digest,str)
        or hashlib.sha256(canonical(unsigned).encode()).hexdigest()!=digest
        or report.get("minecraft_policy_deployed") is not False
        or report.get("model_promotion_authorized") is not False
        or report.get("hidden_resource_state_visible_to_policy") is not False
        or report.get("true_volatility_visible_to_policy") is not False):
        raise ValueError("invalid synthetic history gate provenance")
    seeds=report.get("train_seeds")
    cases=report.get("cases")
    if (not isinstance(seeds,list) or len(seeds)<3 or len(set(seeds))!=len(seeds)
        or not isinstance(cases,list) or len(cases)!=len(seeds)*12):
        raise ValueError("insufficient independent training seed matrix")
    seen=set()
    by_seed={seed:[] for seed in seeds}
    by_regime={regime:[] for regime in REGIMES}
    for case in cases:
        seed=case.get("train_seed")
        regime=case.get("regime")
        rate=case.get("hidden_updates_per_inspection")
        key=(seed,regime,rate)
        if (seed not in by_seed or regime not in by_regime or rate not in RATES
            or key in seen or case.get("heldout_episodes")!=
                report.get("heldout_episodes_per_regime_rate_seed")):
            raise ValueError("missing or repeated evaluation cell")
        seen.add(key)
        b=case.get("scripted_mean_direct_discoveries")
        g=case.get("gated_mean_direct_discoveries")
        n=case.get("neural_mean_direct_discoveries")
        dg=case.get("gated_minus_scripted_mean")
        dn=case.get("neural_minus_scripted_mean")
        if (any(type(x) not in (int,float) or not -32<=x<=32 for x in (dg,dn))
            or any(type(x) not in (int,float) or not 0<=x<=32 for x in (b,g,n))
            or abs(round(g-b,5)-dg)>0.00002 or abs(round(n-b,5)-dn)>0.00002):
            raise ValueError("difference inconsistent with verified directly observed discoveries")
        by_seed[seed].append(dg)
        by_regime[regime].append(dg)
    if len(seen)!=len(cases):raise ValueError("missing heldout cell")
    seed_rows=[{"training_seed":seed,
                "mean_gated_minus_scripted":round(statistics.mean(values),5),
                "negative_cells":sum(x<0 for x in values)}
               for seed,values in sorted(by_seed.items())]
    regime_rows=[{"regime":regime,
                  "mean_gated_minus_scripted":round(statistics.mean(by_regime[regime]),5),
                  "negative_cells":sum(x<0 for x in by_regime[regime])}
                 for regime in REGIMES]
    # Preregistered conservative bar, not a statistical hypothesis test.
    # Even if the bar is passed, this audit does NOT authorize Minecraft.
    seed_consistency=all(row["mean_gated_minus_scripted"]>=0 for row in seed_rows)
    regime_robustness=all(row["mean_gated_minus_scripted"]>=-.25 for row in regime_rows)
    result={
        "schema":SCHEMA,"origin":"SIMULATOR_ONLY_ADMISSION_AUDIT",
        "training_seed_count":len(seeds),
        "heldout_case_count":len(cases),
        "seed_consistency_threshold":0.,
        "minimum_regime_mean_threshold":-.25,
        "seed_consistency_passed":seed_consistency,
        "regime_robustness_passed":regime_robustness,
        "candidate_passed_simulator_admission":
            seed_consistency and regime_robustness,
        "seed_breakdown":seed_rows,
        "regime_breakdown":regime_rows,
        "statistical_significance_established":False,
        "real_forge_generalization_established":False,
        "minecraft_model_promotion_authorized":False}
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,default=Path("history-gated-admission.json"))
    args=parser.parse_args()
    report=audit(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("HISTORY_GATE_ADMISSION simulator_pass="+
          str(report["candidate_passed_simulator_admission"]).lower()+
          " minecraft_promotion=false")

if __name__=="__main__":
    main()
