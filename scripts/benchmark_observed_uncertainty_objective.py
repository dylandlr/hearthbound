#!/usr/bin/env python3
"""Observed-history uncertainty/cost objective: simulator research only.

No privileged simulator truth enters policy features or training reward. A
candidate is trained on a reward observed after inspecting one selected source.
The new objective adds pre-observation uncertainty and inspection-cost terms
derived entirely from the agent's own causal memory.
"""
import argparse
import hashlib
import json
import random
import statistics
from pathlib import Path

from benchmark_rapid_attention_curriculum import RapidWorld, HELDOUT_REGIMES, TRAIN_REGIMES
from benchmark_exploration_aware_attention import train_exploration,SEED_OFFSET,RATES
from benchmark_history_gated_attention import gate
from train_simulated_attention_mlp import MLP,SOURCES,scripted,learned

SCHEMA="hearthbound.observed-uncertainty-objective.v1"
HORIZON=32
WEIGHTS={"uncertainty":0.22,"staleness":0.08,"rapid_reinspect_cost":0.16,
         "never_inspected_bonus":0.28}
ARM_NAMES=("scripted","exploration_neural","history_gated","uncertainty_neural")

def preinspection_reward_terms(world,selected):
    """Every term comes exclusively from direct historical observations."""
    if selected not in range(SOURCES):
        raise ValueError("invalid selected source")
    n=world.observed_count[selected]
    changes=world.observed_changes[selected]
    if type(n)!=int or type(changes)!=int or n<0 or changes<0 or changes>max(0,n-1):
        raise ValueError("invalid direct-history counts")
    unknown=n==0
    # Beta(1,1) posterior on *between-observation* state disagreement,
    # not a privileged estimate of true per-tick resource volatility.
    p=(changes+1)/(max(0,n-1)+2)
    uncertainty=4*p*(1-p)
    age=world.ages[selected]
    if type(age)!=int or age<0:
        raise ValueError("invalid age")
    return {
        "observed_history_uncertainty":uncertainty,
        "staleness":min(age,20)/20,
        "rapid_reinspection":1. if n>0 and age<=2 else 0.,
        "first_inspection":1. if unknown else 0.}

def train_objective(seed,episodes):
    if type(seed)!=int or seed<0 or type(episodes)!=int or episodes<1:
        raise ValueError("invalid training budget")
    model=MLP(seed)
    rng=random.Random(seed+7701)
    for e in range(episodes):
        regime=TRAIN_REGIMES[e%len(TRAIN_REGIMES)]
        rate=RATES[(e//len(TRAIN_REGIMES))%3]
        world=RapidWorld(2000000+seed*100000+e,regime,rate)
        epsilon=.08+.72*max(0.,1.-e/max(1.,episodes*.8))
        for _ in range(HORIZON):
            observed_features=world.features()
            choice=(rng.randrange(SOURCES) if rng.random()<epsilon
                    else learned(model,world))
            terms=preinspection_reward_terms(world,choice)
            direct_reward,_=world.inspect(choice)
            shaped=(direct_reward
                +WEIGHTS["uncertainty"]*terms["observed_history_uncertainty"]
                +WEIGHTS["staleness"]*terms["staleness"]
                +WEIGHTS["never_inspected_bonus"]*terms["first_inspection"]
                -WEIGHTS["rapid_reinspect_cost"]*terms["rapid_reinspection"])
            model.update(observed_features,choice,shaped)
    return model

def evaluate_one(seed,regime,rate,models):
    scores={}
    for arm in ARM_NAMES:
        world=RapidWorld(seed,regime,rate)
        discoveries=0
        inspections=[0]*SOURCES
        consecutive=0
        neural_count=0
        for _ in range(HORIZON):
            if arm=="scripted":
                choice=scripted(world)
                used=False
            elif arm=="history_gated":
                choice,used=gate(world,models["exploration_neural"],consecutive)
            else:
                choice=learned(models[arm],world)
                used=True
            if choice not in range(SOURCES):
                raise ValueError("invalid model choice")
            consecutive=consecutive+1 if used else 0
            neural_count+=int(used)
            inspections[choice]+=1
            _,found=world.inspect(choice)
            discoveries+=int(found)
        scores[arm]={
            "direct_discoveries":discoveries,
            "minimum_source_inspections":min(inspections),
            "distinct_sources_inspected":sum(x>0 for x in inspections),
            "neural_decisions":neural_count}
    return scores

def benchmark(train_seeds=(11,17,23),episodes=240,heldout=40):
    if (not train_seeds or len(set(train_seeds))!=len(train_seeds)
        or any(type(seed)!=int or seed<0 for seed in train_seeds)
        or type(episodes)!=int or episodes<1 or type(heldout)!=int or heldout<1):
        raise ValueError("invalid research budget")
    results=[]
    for train_seed in train_seeds:
        models={"exploration_neural":train_exploration(train_seed+2,episodes),
                "uncertainty_neural":train_objective(train_seed+3,episodes)}
        for regime_idx,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                raw={arm:[] for arm in ARM_NAMES}
                visits={arm:[] for arm in ARM_NAMES}
                gated_uses=[]
                for ep in range(heldout):
                    # Separate training/evaluation seed namespaces; identical
                    # initial seeds are NOT identical latent RNG trajectories.
                    seed=SEED_OFFSET+train_seed*100000+regime_idx*10000+rate*1000+ep
                    row=evaluate_one(seed,regime,rate,models)
                    for arm in ARM_NAMES:
                        raw[arm].append(row[arm]["direct_discoveries"])
                        visits[arm].append(row[arm]["minimum_source_inspections"])
                    gated_uses.append(row["history_gated"]["neural_decisions"])
                scripted_scores=raw["scripted"]
                scores={
                    arm:{"mean_direct_discoveries":round(statistics.mean(raw[arm]),5),
                         "mean_minimum_source_inspections":round(statistics.mean(visits[arm]),5)}
                    for arm in ARM_NAMES}
                deltas={
                    arm:round(statistics.mean(a-b for a,b in
                        zip(raw[arm],scripted_scores)),5)
                    for arm in ARM_NAMES if arm!="scripted"}
                results.append({
                    "train_seed":train_seed,"regime":regime,
                    "hidden_updates_per_inspection":rate,
                    "heldout_episodes":heldout,
                    "policy_scores":scores,
                    "mean_neural_minus_scripted_discoveries":deltas,
                    "gated_mean_neural_decisions":round(statistics.mean(gated_uses),5)})
    # True simulator volatility may influence transitions and synthetic scores;
    # it never enters the policy observation or the selected-source reward.
    report={
        "schema":SCHEMA,"origin":"SIMULATED_ONLY",
        "training_seeds":list(train_seeds),
        "train_episodes_per_seed":episodes,
        "heldout_episodes_per_cell":heldout,
        "evaluation_case_count":len(results),
        "training_reward":"DIRECT_SELECTED_OUTCOME_PLUS_PREINSPECTION_HISTORY_TERMS",
        "posterior_measures":"OBSERVED_DISAGREEMENT_NOT_TRUE_PER_TICK_HAZARD",
        "objective_weights":WEIGHTS,
        "one_source_inspected_per_decision":True,
        "unselected_truth_or_rewards_used_for_learning":False,
        "true_volatility_feature":False,
        "forge_journal_used_for_training":False,
        "minecraft_model_deployed":False,
        "model_promotion_authorized":False,
        "matched_initial_seed_implies_identical_future_trajectories":False,
        "statistical_significance_claimed":False,
        "cases":results}
    report["sha256"]=hashlib.sha256(json.dumps(
        report,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",nargs="+",type=int,default=[11,17,23])
    p.add_argument("--episodes",type=int,default=240)
    p.add_argument("--heldout",type=int,default=40)
    p.add_argument("--output",type=Path,default=Path("observed-uncertainty-objective.json"))
    a=p.parse_args()
    outcome=benchmark(tuple(a.seeds),a.episodes,a.heldout)
    a.output.write_text(json.dumps(outcome,sort_keys=True,indent=2)+"\n")
    print("UNCERTAINTY_OBJECTIVE_SIMULATED cells="+str(len(outcome["cases"]))+
          " live_model_changed=false promotion=false")
if __name__=="__main__":
    main()
