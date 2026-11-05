#!/usr/bin/env python3
"""Equal-update-frequency comparison of one-step and eight-step GRU gradients.

Both arms train from identical initial parameters and receive equal episode,
selected-sensor and optimizer-update budgets. Only whether each loss is
differentiated through earlier recurrent hidden states within a block differs.
Synthetic-only: no model promotion, hidden-world labels or Forge access.
"""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np
from benchmark_gru_truncated_bptt import (
    sequence_gradients, WINDOW, HORIZON, evaluate_one)
from benchmark_recurrent_causal_attention import (
    GRU, HIDDEN, SOURCES, history_input)
from benchmark_frozen_attention_timelines import (
    make_timeline, FrozenWorld, canonical)
from benchmark_rapid_attention_curriculum import (
    HELDOUT_REGIMES, TRAIN_REGIMES)
from benchmark_exploration_aware_attention import SEED_OFFSET,RATES

SCHEMA="hearthbound.gru-matched-optimizer.v1"
ARMS=("scripted","one_step_buffered","eight_step_bptt")

def buffered_one_step_gradients(model,caches,actions,rewards):
    """Differentiate each selected loss through one cell, then sum."""
    if (not caches or len(caches)!=len(actions)
        or len(actions)!=len(rewards) or len(caches)>WINDOW):
        raise ValueError("invalid single-step accumulation window")
    sums={name:np.zeros_like(value) for name,value in model.params.items()}
    for cache,action,reward in zip(caches,actions,rewards):
        gradients=model.gradients(cache,action,reward)
        for name in sums:sums[name]+=gradients[name]
    return sums

def update(model,gradients,number,rate=.016):
    if not 1<=number<=WINDOW or set(gradients)!=set(model.params):
        raise ValueError("invalid optimizer update")
    norm=math.sqrt(sum(float(np.sum(v*v)) for v in gradients.values()))
    scale=rate*min(1.,3./max(1e-12,norm))/number
    for name in model.params:
        model.params[name]-=scale*gradients[name]

def train(seed,episodes,bptt,window=WINDOW):
    if (type(seed)!=int or seed<0 or type(episodes)!=int or episodes<1
        or type(window)!=int or window!=WINDOW or HORIZON%window):
        raise ValueError("invalid controlled training budget")
    model=GRU(seed)
    rng=np.random.default_rng(seed+77231)
    total_updates=0
    for ep in range(episodes):
        regime=TRAIN_REGIMES[ep%len(TRAIN_REGIMES)]
        rate=RATES[(ep//len(TRAIN_REGIMES))%len(RATES)]
        world=FrozenWorld(make_timeline(
            2000000+seed*100000+ep,regime,rate))
        h=np.zeros(HIDDEN)
        prior_action=None
        prior_discovery=prior_available=0
        epsilon=.08+.72*max(0.,1.-ep/max(1.,episodes*.8))
        for _ in range(HORIZON//window):
            caches=[];actions=[];rewards=[]
            for _ in range(window):
                x=history_input(world,prior_action,prior_discovery,prior_available)
                scores,next_h,cache=model.step(x,h)
                action=(int(rng.integers(SOURCES)) if rng.random()<epsilon
                        else int(np.argmax(scores)))
                _,observed=world.inspect(action)
                caches.append(cache)
                actions.append(action)
                rewards.append(float(observed))
                h=next_h
                prior_action=action
                prior_discovery=int(observed)
                prior_available=int(world.memory[action]==1)
            grads=(sequence_gradients(model,caches,actions,rewards)
                   if bptt else buffered_one_step_gradients(
                       model,caches,actions,rewards))
            update(model,grads,len(caches))
            total_updates+=1
    assert total_updates==episodes*(HORIZON//window)
    return model,total_updates

def replay(timeline,models):
    output={}
    for arm in ARMS:
        world=FrozenWorld(timeline)
        h=np.zeros(HIDDEN)
        prior_action=None
        prior_discovery=prior_available=0
        observed=0
        visits=[0]*SOURCES
        for _ in timeline["states"]:
            if arm=="scripted":
                from train_simulated_attention_mlp import scripted
                action=scripted(world)
            else:
                scores,h,_=models[arm].step(history_input(
                    world,prior_action,prior_discovery,prior_available),h)
                action=int(np.argmax(scores))
            visits[action]+=1
            _,found=world.inspect(action)
            observed+=int(found)
            prior_action=action
            prior_discovery=int(found)
            prior_available=int(world.memory[action]==1)
        output[arm]={
            "direct_discoveries":observed,
            "minimum_source_visits":min(visits)}
    return output

def benchmark(seeds=(11,17,23),episodes=180,heldout=30):
    if (not seeds or len(set(seeds))!=len(seeds)
        or any(type(s)!=int or s<0 for s in seeds)
        or type(episodes)!=int or episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid matched optimization experiment")
    cells=[]
    for seed in seeds:
        # Matched weight seed, matching batch size, same exploratory RNG,
        # same per-step reward definition and optimizer update cadence.
        model_seed=seed+101
        control,n0=train(model_seed,episodes,False)
        recurrent,n8=train(model_seed,episodes,True)
        assert n0==n8
        models={"one_step_buffered":control,"eight_step_bptt":recurrent}
        for rid,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                observed={arm:[] for arm in ARMS}
                diversity={arm:[] for arm in ARMS}
                timelines=[]
                for ep in range(heldout):
                    t=make_timeline(
                        SEED_OFFSET+seed*100000+rid*10000+rate*1000+ep,regime,rate)
                    timelines.append(t["sha256"])
                    row=replay(t,models)
                    for arm in ARMS:
                        observed[arm].append(row[arm]["direct_discoveries"])
                        diversity[arm].append(row[arm]["minimum_source_visits"])
                cells.append({
                    "seed":seed,"regime":regime,
                    "updates_per_inspection":rate,
                    "heldout_episodes":heldout,
                    "shared_trajectory_digest":hashlib.sha256(
                        canonical(timelines).encode()).hexdigest(),
                    "mean_direct_discoveries":{
                        arm:round(statistics.mean(observed[arm]),5)
                        for arm in ARMS},
                    "mean_minimum_source_visits":{
                        arm:round(statistics.mean(diversity[arm]),5)
                        for arm in ARMS},
                    "mean_vs_scripted":{
                        arm:round(statistics.mean(
                            a-b for a,b in zip(observed[arm],observed["scripted"])),5)
                        for arm in ARMS if arm!="scripted"}})
    report={"schema":SCHEMA,"origin":"SIMULATED_ONLY",
        "training_seeds":list(seeds),
        "training_episodes_per_seed":episodes,
        "heldout_episodes_per_cell":heldout,
        "training_steps_per_episode":HORIZON,
        "optimizer_updates_per_episode_per_neural_arm":HORIZON//WINDOW,
        "gradient_accumulation_window":WINDOW,
        "learning_rate_per_batch":.016,
        "gradient_clip_norm":3.,
        "same_initial_weights":True,
        "same_model_capacity":True,
        "same_update_cadence":True,
        "same_observation_budget":True,
        "training_action_histories_guaranteed_identical":False,
        "gradient_horizon_only_intended_difference":True,
        "heldout_latent_timelines_shared":True,
        "unselected_outcome_labels_used":False,
        "forge_model_deployed":False,
        "minecraft_model_promotion_authorized":False,
        "statistical_significance_claimed":False,
        "cases":cells}
    report["sha256"]=hashlib.sha256(canonical(report).encode()).hexdigest()
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",type=int,nargs="+",default=[11,17,23])
    p.add_argument("--episodes",type=int,default=180)
    p.add_argument("--heldout",type=int,default=30)
    p.add_argument("--output",type=Path,default=Path("gru-matched-optimizer.json"))
    a=p.parse_args()
    result=benchmark(tuple(a.seeds),a.episodes,a.heldout)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("GRU_MATCHED_UPDATES cases="+str(len(result["cases"]))+
          " promotion=false")

if __name__=="__main__":
    main()
