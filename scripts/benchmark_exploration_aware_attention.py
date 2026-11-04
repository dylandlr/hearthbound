#!/usr/bin/env python3
"""Train and evaluate an exploration-aware MLP using only causal sensor history.

All outcomes are synthetic. The only training reward is obtained *after* an
inspection, from the selected source and pre-inspection personal history.
Neither true volatility nor unseen source states enter MLP observations.
"""
import argparse
import hashlib
import json
import math
import random
import statistics
from pathlib import Path

from benchmark_rapid_attention_curriculum import (
    RapidWorld, train as baseline_train, HELDOUT_REGIMES,
    TRAIN_REGIMES, HORIZON)
from train_simulated_attention_mlp import MLP, SOURCES, scripted, learned

SCHEMA="hearthbound.exploration-aware-attention.v1"
SEED_OFFSET=9100000
RATES=(1,2,4)
ARM_NAMES=("legacy_style","mixed_rapid_curriculum","exploration_aware")

def train_exploration(seed,episodes,novelty_bonus=.35,staleness_bonus=.12):
    if type(seed)!=int or type(episodes)!=int or episodes<1:
        raise ValueError("invalid training parameters")
    if not (math.isfinite(novelty_bonus) and 0<=novelty_bonus<=1
            and math.isfinite(staleness_bonus) and 0<=staleness_bonus<=.5):
        raise ValueError("invalid exploration incentives")
    model=MLP(seed)
    rng=random.Random(seed+7701)
    for e in range(episodes):
        regime=TRAIN_REGIMES[e%len(TRAIN_REGIMES)]
        rate=RATES[(e//len(TRAIN_REGIMES))%len(RATES)]
        world=RapidWorld(2000000+seed*100000+e,regime,rate)
        epsilon=.08+.72*max(0.,1.-e/max(1.,episodes*.8))
        for _ in range(HORIZON):
            x=world.features()
            choice=(rng.randrange(SOURCES) if rng.random()<epsilon
                    else learned(model,world))
            # Novelty and age are derived from this agent's OWN memory before
            # the observation, not from world truth or future outcomes.
            unknown=world.memory[choice]==-1
            age=world.ages[choice]
            reward,_=world.inspect(choice)
            shaped=reward+(novelty_bonus if unknown else 0.)+(
                staleness_bonus if age>=12 else 0.)
            model.update(x,choice,shaped)
    return model

def one_episode(seed,regime,rate,models):
    # Every policy starts with the same latent simulator seed.
    # Their later RNG trajectories may diverge, so this is a matched initial
    # condition, NOT identical intervening hidden state trajectories.
    outcomes={}
    selections={}
    for name in ("scripted",)+ARM_NAMES:
        world=RapidWorld(seed,regime,rate)
        direct=0
        visited=set()
        picks=[0]*SOURCES
        for _ in range(HORIZON):
            action=(scripted(world) if name=="scripted"
                    else learned(models[name],world))
            picks[action]+=1
            visited.add(action)
            _,found=world.inspect(action)
            direct+=int(found)
        outcomes[name]=direct
        selections[name]={
            "unique_sources_inspected":len(visited),
            "minimum_source_inspections":min(picks),
            "maximum_source_inspections":max(picks)}
    return outcomes,selections

def benchmark(train_seeds=(11,17,23),episodes=240,heldout=40,
              novelty_bonus=.35,staleness_bonus=.12):
    if (not train_seeds or any(type(x)!=int or x<0 for x in train_seeds)
        or len(set(train_seeds))!=len(train_seeds)
        or type(episodes)!=int or episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid evaluation specification")
    cases=[]
    for train_seed in train_seeds:
        models={
            "legacy_style":baseline_train(train_seed,episodes,False),
            "mixed_rapid_curriculum":baseline_train(train_seed+1,episodes,True),
            "exploration_aware":train_exploration(
                train_seed+2,episodes,novelty_bonus,staleness_bonus)}
        for regime_id,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                results={k:[] for k in ("scripted",)+ARM_NAMES}
                distinct={k:[] for k in ("scripted",)+ARM_NAMES}
                minimum={k:[] for k in ("scripted",)+ARM_NAMES}
                for case in range(heldout):
                    # Held-out seed namespace is far outside training seeds.
                    seed=SEED_OFFSET+train_seed*100000+regime_id*10000+rate*1000+case
                    observations,counts=one_episode(seed,regime,rate,models)
                    for k in results:
                        results[k].append(observations[k])
                        distinct[k].append(counts[k]["unique_sources_inspected"])
                        minimum[k].append(counts[k]["minimum_source_inspections"])
                summaries={}
                for name in results:
                    summaries[name]={
                        "mean_direct_discoveries":round(statistics.mean(results[name]),5),
                        "mean_distinct_sources_visited":round(statistics.mean(distinct[name]),5),
                        "mean_minimum_source_visits":round(statistics.mean(minimum[name]),5)}
                differences={}
                for name in ARM_NAMES:
                    difference=[a-b for a,b in zip(results[name],results["scripted"])]
                    differences[name]={
                        "mean_neural_minus_scripted_discoveries":
                            round(statistics.mean(difference),5),
                        "episodes_better_than_scripted":
                            sum(x>0 for x in difference),
                        "episodes_worse_than_scripted":
                            sum(x<0 for x in difference),
                        "episodes_tied_with_scripted":
                            sum(x==0 for x in difference)}
                cases.append({
                    "training_seed":train_seed,
                    "regime":regime,
                    "hidden_updates_per_inspection":rate,
                    "heldout_episodes":heldout,
                    "summaries":summaries,
                    "differences":differences})
    # Promotion is deliberately forbidden independent of any impressive
    # synthetic gain. This is research evidence, not an action contract.
    result={
        "schema":SCHEMA,
        "origin":"SIMULATED_ONLY",
        "training_seeds":list(train_seeds),
        "training_episodes_per_policy_per_seed":episodes,
        "heldout_episodes_per_seed_regime_rate":heldout,
        "heldout_seed_namespace":SEED_OFFSET,
        "regimes":list(HELDOUT_REGIMES),
        "update_rates":list(RATES),
        "exploration_bonus_on_first_direct_inspection":novelty_bonus,
        "staleness_bonus_on_selected_old_memory":staleness_bonus,
        "observation_width":16,
        "source_count":4,
        "one_inspection_per_decision":True,
        "only_selected_source_rewards_available_to_training":True,
        "hidden_truth_visible_to_policy":False,
        "true_volatility_visible_to_policy":False,
        "real_minecraft_journals_used_for_training":False,
        "minecraft_model_deployed":False,
        "model_promotion_authorized":False,
        "causal_superiority_claimed":False,
        "world_rng_paths_identical_after_policy_divergence":False,
        "cases":cases}
    result["sha256"]=hashlib.sha256(json.dumps(
        result,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return result

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--seeds",nargs="+",type=int,default=[11,17,23])
    cli.add_argument("--episodes",type=int,default=240)
    cli.add_argument("--heldout",type=int,default=40)
    cli.add_argument("--novelty",type=float,default=.35)
    cli.add_argument("--staleness",type=float,default=.12)
    cli.add_argument("--output",type=Path,default=Path("exploration-aware-attention.json"))
    args=cli.parse_args()
    outcome=benchmark(tuple(args.seeds),args.episodes,args.heldout,args.novelty,args.staleness)
    args.output.write_text(json.dumps(outcome,sort_keys=True,indent=2)+"\n")
    print("EXPLORATION_ATTENTION_SIMULATED cases="+str(len(outcome["cases"]))+
          " training_seeds="+str(len(outcome["training_seeds"]))+
          " model_promoted=false forge_execution=false")

if __name__=="__main__":
    main()
