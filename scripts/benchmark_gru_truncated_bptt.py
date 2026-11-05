#!/usr/bin/env python3
"""Eight-decision truncated BPTT for causal GRU source attention.

The recurrent gradient propagates through prior hidden states within each
chunk; unlike v0.14.5's one-step update, update/reset/candidate-gate feedback
from later selected observations reaches earlier sequence steps.

Synthetic-only. Each training label is the chosen source's actual observed
discovery. Never train on source truth that was not directly inspected.
"""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np
from benchmark_recurrent_causal_attention import (
    GRU, HIDDEN, SOURCES, INPUT, history_input, train as train_one_step,
    SCHEMA as OLD_SCHEMA, sigmoid)
from benchmark_frozen_attention_timelines import (
    FrozenWorld, make_timeline, canonical)
from benchmark_exploration_aware_attention import (
    SEED_OFFSET, RATES)
from benchmark_rapid_attention_curriculum import (
    HELDOUT_REGIMES, TRAIN_REGIMES)
from train_simulated_attention_mlp import scripted

SCHEMA="hearthbound.gru-truncated-bptt.v1"
WINDOW=8
HORIZON=32
POLICIES=("scripted","one_step_gru","tbptt_gru")

def sequence_gradients(model,caches,actions,rewards):
    """Exact derivative for sum of selected-output squared errors on a chunk."""
    if (not caches or len(caches)!=len(actions)
        or len(caches)!=len(rewards) or len(caches)>WINDOW):
        raise ValueError("invalid temporal training sequence")
    params=model.params
    grads={name:np.zeros_like(weight) for name,weight in params.items()}
    upstream=np.zeros(HIDDEN)
    for cache,action,reward in reversed(list(zip(caches,actions,rewards))):
        if (type(action)!=int or not 0<=action<SOURCES
            or not math.isfinite(float(reward))):
            raise ValueError("invalid selected outcome")
        x,previous,z,r,n,current=cache
        error=float((params["Wo"]@current+params["bo"])[action]-reward)
        grads["Wo"][action]+=error*current
        grads["bo"][action]+=error
        dh=upstream+error*params["Wo"][action]
        d_n_pre=(dh*(1-z))*(1-n*n)
        d_z_pre=(dh*(previous-n))*z*(1-z)
        d_rh=params["Un"].T@d_n_pre
        d_r_pre=(d_rh*previous)*r*(1-r)
        grads["Wn"]+=np.outer(d_n_pre,x)
        grads["Un"]+=np.outer(d_n_pre,r*previous)
        grads["bn"]+=d_n_pre
        grads["Wz"]+=np.outer(d_z_pre,x)
        grads["Uz"]+=np.outer(d_z_pre,previous)
        grads["bz"]+=d_z_pre
        grads["Wr"]+=np.outer(d_r_pre,x)
        grads["Ur"]+=np.outer(d_r_pre,previous)
        grads["br"]+=d_r_pre
        # Backpropagate to the previous recurrent state, including the
        # direct update-gate path, candidate-state path, reset and update.
        upstream=(dh*z + d_rh*r
                  +params["Uz"].T@d_z_pre +params["Ur"].T@d_r_pre)
    return grads

def apply_sequence_update(model,caches,actions,rewards,rate=.016):
    gradients=sequence_gradients(model,caches,actions,rewards)
    magnitude=math.sqrt(sum(float(np.sum(v*v)) for v in gradients.values()))
    clip=min(1.,3./max(1e-12,magnitude))
    scale=rate*clip/len(caches)
    for name in model.params:
        model.params[name]-=scale*gradients[name]

def train_bptt(seed,episodes,window=WINDOW):
    if (type(seed)!=int or seed<0 or type(episodes)!=int or episodes<1
        or type(window)!=int or window<2 or HORIZON%window):
        raise ValueError("invalid truncated BPTT configuration")
    rng=np.random.default_rng(seed+77231)
    model=GRU(seed)
    for ep in range(episodes):
        regime=TRAIN_REGIMES[ep%len(TRAIN_REGIMES)]
        rate=RATES[(ep//len(TRAIN_REGIMES))%len(RATES)]
        world=FrozenWorld(make_timeline(2000000+seed*100000+ep,regime,rate))
        hidden=np.zeros(HIDDEN)
        previous_action=None
        previous_discovery=previous_available=0
        epsilon=.08+.72*max(0.,1.-ep/max(1.,episodes*.8))
        for _ in range(HORIZON//window):
            caches=[];actions=[];rewards=[]
            for _ in range(window):
                x=history_input(
                    world,previous_action,previous_discovery,previous_available)
                values,next_hidden,cache=model.step(x,hidden)
                selected=(int(rng.integers(SOURCES)) if rng.random()<epsilon
                          else int(np.argmax(values)))
                _,discovered=world.inspect(selected)
                caches.append(cache);actions.append(selected)
                rewards.append(float(discovered))
                hidden=next_hidden
                previous_action=selected
                previous_discovery=int(discovered)
                previous_available=int(world.memory[selected]==1)
            apply_sequence_update(model,caches,actions,rewards)
            # Hidden state persists numerically, but its gradient is detached
            # at chunk boundaries: true truncated, not full-episode BPTT.
    return model

def evaluate_one(timeline,models):
    results={}
    for name in POLICIES:
        world=FrozenWorld(timeline)
        hidden=np.zeros(HIDDEN)
        prev_action=None
        prev_discovery=prev_available=0
        discoveries=0
        counts=[0]*SOURCES
        for _ in timeline["states"]:
            if name=="scripted":
                choice=scripted(world)
            else:
                x=history_input(world,prev_action,prev_discovery,prev_available)
                scores,hidden,_=models[name].step(x,hidden)
                choice=int(np.argmax(scores))
            counts[choice]+=1
            _,found=world.inspect(choice)
            discoveries+=int(found)
            prev_action=choice
            prev_discovery=int(found)
            prev_available=int(world.memory[choice]==1)
        results[name]={
            "direct_discoveries":discoveries,
            "minimum_source_visits":min(counts),
            "distinct_sources":sum(x>0 for x in counts)}
    return results

def benchmark(seeds=(11,17,23),episodes=180,heldout=30,window=WINDOW):
    if (not seeds or len(set(seeds))!=len(seeds)
        or any(type(s)!=int or s<0 for s in seeds)
        or type(episodes)!=int or episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid held-out study")
    cells=[]
    for seed in seeds:
        models={"one_step_gru":train_one_step(seed+101,episodes),
                "tbptt_gru":train_bptt(seed+101,episodes,window)}
        for rix,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                scores={arm:[] for arm in POLICIES}
                diversities={arm:[] for arm in POLICIES}
                trajectory_digests=[]
                for i in range(heldout):
                    t=make_timeline(
                        SEED_OFFSET+seed*100000+rix*10000+rate*1000+i,regime,rate)
                    trajectory_digests.append(t["sha256"])
                    results=evaluate_one(t,models)
                    for arm in POLICIES:
                        scores[arm].append(results[arm]["direct_discoveries"])
                        diversities[arm].append(results[arm]["minimum_source_visits"])
                cells.append({
                    "training_seed":seed,"regime":regime,"updates_per_inspection":rate,
                    "heldout_episodes":heldout,
                    "shared_trajectory_manifest_sha256":hashlib.sha256(
                        canonical(trajectory_digests).encode()).hexdigest(),
                    "mean_direct_discoveries":{
                        a:round(statistics.mean(v),5) for a,v in scores.items()},
                    "mean_minimum_source_visits":{
                        a:round(statistics.mean(v),5) for a,v in diversities.items()},
                    "mean_vs_scripted":{
                        a:round(statistics.mean(x-y for x,y in
                            zip(scores[a],scores["scripted"])),5)
                        for a in POLICIES if a!="scripted"}})
    result={
        "schema":SCHEMA,"origin":"SIMULATED_ONLY",
        "train_seeds":list(seeds),"episodes_per_training_seed":episodes,
        "heldout_episodes_per_case":heldout,
        "gradient":"TRUNCATED_BPTT_THROUGH_RECURRENT_HIDDEN_STATE",
        "bptt_window":window,
        "old_gru_baseline":"ONE_STEP_TRUNCATED_RECURRENT_GATE_GRADIENT",
        "fixed_trajectory_controls":True,
        "policy_sees_hidden_source_truth":False,
        "unselected_rewards_used_for_training":False,
        "real_forge_weights_changed":False,
        "minecraft_model_promotion_authorized":False,
        "statistical_significance_claimed":False,
        "cases":cells}
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",nargs="+",type=int,default=[11,17,23])
    parser.add_argument("--episodes",type=int,default=180)
    parser.add_argument("--heldout",type=int,default=30)
    parser.add_argument("--output",type=Path,default=Path("gru-bptt-attention.json"))
    args=parser.parse_args()
    result=benchmark(tuple(args.seeds),args.episodes,args.heldout)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("GRU_TRUNCATED_BPTT_SIMULATOR cases="+str(len(result["cases"]))+
          " model_promotion=false")

if __name__=="__main__":
    main()
