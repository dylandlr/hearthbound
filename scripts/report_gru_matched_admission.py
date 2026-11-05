#!/usr/bin/env python3
"""Signed, fail-closed seed/regime audit of matched-update GRU comparisons."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

SCHEMA="hearthbound.gru-matched-optimizer-admission.v1"
REGIMES=("in_distribution","low_volatility","unequal_volatility","high_volatility")
RATES=(1,2,4)
ARMS=("scripted","one_step_buffered","eight_step_bptt")
def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def audit(report):
    unsigned={k:v for k,v in report.items() if k!="sha256"}
    if (report.get("schema")!="hearthbound.gru-matched-optimizer.v1"
        or report.get("origin")!="SIMULATED_ONLY"
        or report.get("sha256")!=hashlib.sha256(canonical(unsigned).encode()).hexdigest()
        or report.get("same_update_cadence") is not True
        or report.get("same_initial_weights") is not True
        or report.get("heldout_latent_timelines_shared") is not True
        or report.get("unselected_outcome_labels_used") is not False
        or report.get("minecraft_model_promotion_authorized") is not False):
        raise ValueError("unsupported matched-optimizer provenance")
    seeds=report.get("training_seeds")
    cases=report.get("cases")
    if (not isinstance(seeds,list) or len(seeds)<3 or len(set(seeds))!=len(seeds)
        or any(type(seed)!=int or seed<0 for seed in seeds)
        or not isinstance(cases,list) or len(cases)!=len(seeds)*12):
        raise ValueError("incomplete training seed matrix")
    seen=set()
    pairs=[]
    by_seed={s:[] for s in seeds}
    by_regime={r:[] for r in REGIMES}
    bptt_vs_scripted=[]
    for row in cases:
        seed=row.get("seed");regime=row.get("regime")
        rate=row.get("updates_per_inspection")
        key=(seed,regime,rate)
        if (seed not in by_seed or regime not in by_regime or rate not in RATES
            or key in seen or row.get("heldout_episodes")!=
                report.get("heldout_episodes_per_cell")):
            raise ValueError("duplicate or missing matched evaluation cell")
        seen.add(key)
        scores=row.get("mean_direct_discoveries")
        deltas=row.get("mean_vs_scripted")
        if (not isinstance(scores,dict) or set(scores)!=set(ARMS)
            or not isinstance(deltas,dict)
            or set(deltas)!={"one_step_buffered","eight_step_bptt"}):
            raise ValueError("incomplete policy result")
        for arm in ARMS:
            v=scores[arm]
            if type(v) not in (int,float) or not 0<=v<=32:
                raise ValueError("invalid direct discovery score")
        for arm in ARMS[1:]:
            if (type(deltas[arm]) not in (int,float) or
                abs(round(scores[arm]-scores["scripted"],5)-deltas[arm])>0.00002):
                raise ValueError("delta not supported by direct observations")
        paired=deltas["eight_step_bptt"]-deltas["one_step_buffered"]
        pairs.append(paired)
        by_seed[seed].append(paired)
        by_regime[regime].append(paired)
        bptt_vs_scripted.append(deltas["eight_step_bptt"])
    seed_rows=[{"seed":s,"bptt_minus_buffered":round(statistics.mean(v),5)}
               for s,v in sorted(by_seed.items())]
    regime_rows=[{"regime":r,"bptt_minus_buffered":round(statistics.mean(by_regime[r]),5)}
                 for r in REGIMES]
    seeds_pass=all(row["bptt_minus_buffered"]>=0 for row in seed_rows)
    wins_scripted=all(statistics.mean(
        row["mean_vs_scripted"]["eight_step_bptt"] for row in cases
        if row["seed"]==seed)>=0 for seed in seeds)
    result={
        "schema":SCHEMA,"origin":"VERIFIED_SIMULATED_ONLY",
        "case_count":len(cases),
        "seed_count":len(seeds),
        "bptt_minus_buffered_mean":round(statistics.mean(pairs),5),
        "bptt_vs_scripted_mean":round(statistics.mean(bptt_vs_scripted),5),
        "seed_rows":seed_rows,
        "regime_rows":regime_rows,
        "bptt_better_in_every_seed":seeds_pass,
        "bptt_not_worse_than_scripted_in_every_seed":wins_scripted,
        "candidate_passed_simulator_admission":seeds_pass and wins_scripted,
        "real_forge_advantage_established":False,
        "statistical_significance_established":False,
        "minecraft_model_promotion_authorized":False}
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("input",type=Path)
    parser.add_argument("--output",type=Path,default=Path("gru-matched-admission.json"))
    args=parser.parse_args()
    out=audit(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("MATCHED_GRU_ADMISSION accepted="+str(out["candidate_passed_simulator_admission"]).lower()
          +" forge_promotion=false")
if __name__=="__main__":
    main()
