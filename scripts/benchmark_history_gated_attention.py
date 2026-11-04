#!/usr/bin/env python3
"""Conservative causal-history gate between scripted and trained attention.

All learning and evaluation are simulator-only. Gate uses exactly the citizen's
own previous selected-source observations, not hidden simulator truth or true
volatility. Threshold fixed before evaluating heldout cases.
"""
import argparse
import hashlib
import json
import statistics
from pathlib import Path

from benchmark_exploration_aware_attention import train_exploration,SEED_OFFSET,RATES
from benchmark_rapid_attention_curriculum import RapidWorld,HELDOUT_REGIMES
from train_simulated_attention_mlp import SOURCES,scripted,learned

SCHEMA="hearthbound.history-gated-attention.v1"
HORIZON=32
# Conservative defaults frozen before heldout testing. Do not tune on Forge D.
MIN_DIRECT_OBSERVATIONS_PER_SOURCE=3
MIN_OBSERVED_CHANGE_RATE_SPREAD=.40
MAX_CONSECUTIVE_NEURAL_CHOICE=2

def gate(world,model,last_neural_choices=0):
    """Return action and whether neural was used, from own observation memory."""
    counts=world.observed_count
    if (len(counts)!=SOURCES or len(world.observed_changes)!=SOURCES
        or len(world.memory)!=SOURCES or len(world.ages)!=SOURCES
        or type(last_neural_choices)!=int or last_neural_choices<0):
        raise ValueError("invalid causal observation history")
    fallback=scripted(world)
    if (min(counts)<MIN_DIRECT_OBSERVATIONS_PER_SOURCE
        or last_neural_choices>=MAX_CONSECUTIVE_NEURAL_CHOICE):
        return fallback,False
    history=[world.observed_changes[i]/(counts[i]-1) for i in range(SOURCES)]
    if max(history)-min(history)<MIN_OBSERVED_CHANGE_RATE_SPREAD:
        return fallback,False
    candidate=learned(model,world)
    if candidate<0 or candidate>=SOURCES:
        raise ValueError("invalid model selected source")
    return candidate,True

def evaluate_episode(seed,regime,rate,model):
    outcomes={}
    for name in ("scripted","neural","gated"):
        world=RapidWorld(seed,regime,rate)
        visits=[0]*SOURCES
        discoveries=0
        neural_decisions=0
        consecutive=0
        for _ in range(HORIZON):
            if name=="scripted":
                action=scripted(world)
                used=False
            elif name=="neural":
                action=learned(model,world)
                used=True
            else:
                action,used=gate(world,model,consecutive)
            consecutive=consecutive+1 if used else 0
            neural_decisions+=int(used)
            visits[action]+=1
            _,found=world.inspect(action)
            discoveries+=int(found)
        outcomes[name]={
            "direct_discoveries":discoveries,
            "neural_choices":neural_decisions,
            "distinct_sources":sum(x>0 for x in visits),
            "minimum_source_visits":min(visits)}
    return outcomes

def benchmark(train_seeds=(11,17,23),episodes=240,heldout=40):
    if (not train_seeds or len(set(train_seeds))!=len(train_seeds)
        or any(type(x)!=int or x<0 for x in train_seeds)
        or type(episodes)!=int or episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid benchmark configuration")
    cases=[]
    for train_seed in train_seeds:
        model=train_exploration(train_seed+2,episodes)
        for regime_id,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                observations={name:[] for name in ("scripted","neural","gated")}
                choices=[]
                diversity=[]
                for episode in range(heldout):
                    world_seed=SEED_OFFSET+train_seed*100000+regime_id*10000+rate*1000+episode
                    data=evaluate_episode(world_seed,regime,rate,model)
                    for name in observations:
                        observations[name].append(data[name]["direct_discoveries"])
                    choices.append(data["gated"]["neural_choices"])
                    diversity.append(data["gated"]["minimum_source_visits"])
                base=observations["scripted"]
                case={
                    "train_seed":train_seed,
                    "regime":regime,
                    "hidden_updates_per_inspection":rate,
                    "heldout_episodes":heldout,
                    "scripted_mean_direct_discoveries":round(statistics.mean(base),5),
                    "neural_mean_direct_discoveries":round(statistics.mean(observations["neural"]),5),
                    "gated_mean_direct_discoveries":round(statistics.mean(observations["gated"]),5),
                    "gated_mean_neural_decisions_per_episode":round(statistics.mean(choices),5),
                    "gated_mean_least_visited_source_count":round(statistics.mean(diversity),5),
                    "neural_minus_scripted_mean":round(
                        statistics.mean(a-b for a,b in zip(observations["neural"],base)),5),
                    "gated_minus_scripted_mean":round(
                        statistics.mean(a-b for a,b in zip(observations["gated"],base)),5)}
                cases.append(case)
    rows=[]
    for regime in HELDOUT_REGIMES:
        data=[v for v in cases if v["regime"]==regime]
        rows.append({
            "regime":regime,
            "neural_mean_difference":round(statistics.mean(x["neural_minus_scripted_mean"] for x in data),5),
            "gated_mean_difference":round(statistics.mean(x["gated_minus_scripted_mean"] for x in data),5),
            "neural_negative_cases":sum(x["neural_minus_scripted_mean"]<0 for x in data),
            "gated_negative_cases":sum(x["gated_minus_scripted_mean"]<0 for x in data),
            "gated_neural_choices_mean":round(statistics.mean(
                x["gated_mean_neural_decisions_per_episode"] for x in data),5)})
    result={
        "schema":SCHEMA,
        "origin":"SIMULATED_ONLY",
        "train_seeds":list(train_seeds),
        "train_episodes_per_seed":episodes,
        "heldout_episodes_per_regime_rate_seed":heldout,
        "gate_contract":{
            "min_direct_observations_each_source":MIN_DIRECT_OBSERVATIONS_PER_SOURCE,
            "minimum_empirical_change_rate_spread":MIN_OBSERVED_CHANGE_RATE_SPREAD,
            "max_consecutive_neural_selections":MAX_CONSECUTIVE_NEURAL_CHOICE},
        "policy_features":"PERSONAL_DIRECT_OBSERVATION_HISTORY_ONLY",
        "hidden_resource_state_visible_to_policy":False,
        "true_volatility_visible_to_policy":False,
        "training_counterfactual_rewards_inferred":False,
        "forge_model_file_changed":False,
        "minecraft_policy_deployed":False,
        "model_promotion_authorized":False,
        "causal_superiority_claimed":False,
        "cases":cases,"regimes":rows}
    result["sha256"]=hashlib.sha256(json.dumps(
        result,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return result

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--seeds",type=int,nargs="+",default=[11,17,23])
    cli.add_argument("--episodes",type=int,default=240)
    cli.add_argument("--heldout",type=int,default=40)
    cli.add_argument("--output",type=Path,default=Path("history-gated-attention.json"))
    args=cli.parse_args()
    result=benchmark(tuple(args.seeds),args.episodes,args.heldout)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("SIMULATOR_HISTORY_GATED cases="+str(len(result["cases"]))+
          " Minecraft_deployment=false promotion=false")

if __name__=="__main__":
    main()
