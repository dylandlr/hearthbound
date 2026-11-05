#!/usr/bin/env python3
"""Verify 36 synthetic GRU vs MLP vs scripted cells and deny unsafe promotion."""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

ARMS=("scripted","exploration_mlp","gru")
REGIMES=("in_distribution","low_volatility","unequal_volatility","high_volatility")
RATES=(1,2,4)
SCHEMA="hearthbound.recurrent-attention-admission.v1"

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False)

def audit(report):
    unsigned={k:v for k,v in report.items() if k!="sha256"}
    if (report.get("schema")!="hearthbound.recurrent-causal-attention.v1"
        or report.get("origin")!="SIMULATED_ONLY"
        or report.get("sha256")!=hashlib.sha256(canonical(unsigned).encode()).hexdigest()
        or report.get("matched_hidden_trajectories_per_episode") is not True
        or report.get("policy_can_read_future_timeline") is not False
        or report.get("training_uses_unselected_source_rewards") is not False
        or report.get("real_forge_model_changed") is not False
        or report.get("minecraft_model_promotion_authorized") is not False):
        raise ValueError("unsupported recurrent evidence")
    seeds=report.get("training_seeds")
    cells=report.get("cases")
    if (not isinstance(seeds,list) or len(seeds)<3 or len(set(seeds))!=len(seeds)
        or not isinstance(cells,list) or len(cells)!=len(seeds)*12):
        raise ValueError("incomplete three-training-seed study")
    seen=set()
    by_seed={s:[] for s in seeds}
    by_regime={r:[] for r in REGIMES}
    means={"gru":[],"exploration_mlp":[]}
    for cell in cells:
        s=cell.get("train_seed")
        r=cell.get("regime")
        rate=cell.get("updates_per_inspection")
        k=(s,r,rate)
        if (s not in by_seed or r not in by_regime or rate not in RATES
            or k in seen or cell.get("heldout_episodes")!=report.get("heldout_episodes_per_cell")):
            raise ValueError("duplicate/missing heldout cell")
        seen.add(k)
        scores=cell.get("mean_direct_discoveries")
        deltas=cell.get("mean_vs_scripted")
        if (not isinstance(scores,dict) or set(scores)!=set(ARMS)
            or not isinstance(deltas,dict) or set(deltas)!={"gru","exploration_mlp"}):
            raise ValueError("invalid policy matrix")
        for arm in ARMS:
            x=scores[arm]
            if type(x) not in (float,int) or not 0<=x<=32:
                raise ValueError("impossible discovery count")
        for arm in means:
            delta=deltas[arm]
            if (type(delta) not in (int,float)
                or abs(round(scores[arm]-scores["scripted"],5)-delta)>0.00002):
                raise ValueError("difference inconsistent with direct observations")
            means[arm].append(delta)
        by_seed[s].append(deltas["gru"])
        by_regime[r].append(deltas["gru"])
    seed_rows=[{"seed":s,"gru_minus_scripted":round(statistics.mean(v),5)}
               for s,v in sorted(by_seed.items())]
    regimes=[{"regime":r,"gru_minus_scripted":round(statistics.mean(by_regime[r]),5)}
             for r in REGIMES]
    # A conservative rejection test only. Even if satisfied, live deployment
    # would require additional independent benchmarks, Java parity and Forge.
    stable_seeds=all(x["gru_minus_scripted"]>=0 for x in seed_rows)
    stable_regimes=all(x["gru_minus_scripted"]>=-.25 for x in regimes)
    output={
        "schema":SCHEMA,"origin":"VERIFIED_SIMULATOR_ONLY_COMPARISON",
        "training_seed_count":len(seeds),
        "heldout_case_count":len(cells),
        "gru_mean_vs_scripted":round(statistics.mean(means["gru"]),5),
        "mlp_mean_vs_scripted":round(statistics.mean(means["exploration_mlp"]),5),
        "gru_minus_mlp_mean":round(statistics.mean(
            g-m for g,m in zip(means["gru"],means["exploration_mlp"])),5),
        "seed_results":seed_rows,"regime_results":regimes,
        "seed_consistency_passed":stable_seeds,
        "regime_robustness_passed":stable_regimes,
        "passed_simulator_admission":stable_seeds and stable_regimes,
        "statistical_significance_established":False,
        "real_forge_advantage_established":False,
        "model_promotion_authorized":False}
    output["sha256"]=hashlib.sha256(canonical(output).encode()).hexdigest()
    return output

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("input",type=Path)
    cli.add_argument("--output",type=Path,default=Path("recurrent-attention-admission.json"))
    args=cli.parse_args()
    output=audit(json.loads(args.input.read_text()))
    args.output.write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    print("RECURRENT_ATTENTION_ADMISSION accepted="+str(output["passed_simulator_admission"]).lower()
          +" live_promotion=false")
if __name__=="__main__":
    main()
