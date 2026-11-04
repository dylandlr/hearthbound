#!/usr/bin/env python3
"""Train a small GRU on selected-source outcomes; compare on frozen trajectories.

The GRU state persists across decisions. Training uses one-step truncated
gradients (no BPTT through previous hidden states); recurrent weights ARE
trained, but long-range credit assignment is not. No hidden world truth or
unselected rewards are available to the policy.
"""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np

from benchmark_frozen_attention_timelines import (
    make_timeline, FrozenWorld, ARMS as FROZEN_ARMS, canonical)
from benchmark_exploration_aware_attention import train_exploration, SEED_OFFSET, RATES
from benchmark_rapid_attention_curriculum import HELDOUT_REGIMES, TRAIN_REGIMES
from train_simulated_attention_mlp import SOURCES, scripted, learned

SCHEMA="hearthbound.recurrent-causal-attention.v1"
INPUT=16+SOURCES+2
HIDDEN=12
HORIZON=32
ARMS=("scripted","exploration_mlp","gru")

def sigmoid(a):
    return 1.0/(1.0+np.exp(-np.clip(a,-35,35)))

class GRU:
    def __init__(self,seed):
        rng=np.random.default_rng(seed)
        self.params={}
        for g in ("z","r","n"):
            self.params["W"+g]=rng.normal(0,.075,(HIDDEN,INPUT))
            self.params["U"+g]=rng.normal(0,.075,(HIDDEN,HIDDEN))
            self.params["b"+g]=np.zeros(HIDDEN)
        self.params["Wo"]=rng.normal(0,.075,(SOURCES,HIDDEN))
        self.params["bo"]=np.zeros(SOURCES)

    def step(self,x,h):
        x=np.asarray(x,dtype=float)
        h=np.asarray(h,dtype=float)
        if (x.shape!=(INPUT,) or h.shape!=(HIDDEN,)
            or not np.all(np.isfinite(x)) or not np.all(np.isfinite(h))):
            raise ValueError("invalid recurrent observation")
        p=self.params
        z=sigmoid(p["Wz"]@x+p["Uz"]@h+p["bz"])
        r=sigmoid(p["Wr"]@x+p["Ur"]@h+p["br"])
        n=np.tanh(p["Wn"]@x+p["Un"]@(r*h)+p["bn"])
        next_h=(1-z)*n+z*h
        scores=p["Wo"]@next_h+p["bo"]
        return scores,next_h,(x,h,z,r,n,next_h)

    def gradients(self,cache,action,reward):
        if (type(action)!=int or not 0<=action<SOURCES
            or not math.isfinite(reward)):
            raise ValueError("reward must come from selected inspection")
        x,previous,z,r,n,h=cache
        p=self.params
        error=float((p["Wo"]@h+p["bo"])[action]-reward)
        grad={name:np.zeros_like(value) for name,value in p.items()}
        grad["Wo"][action]=error*h
        grad["bo"][action]=error
        dh=error*p["Wo"][action].copy()
        dn=dh*(1-z)
        dz=dh*(previous-n)
        dn_pre=dn*(1-n*n)
        grad["Wn"]=np.outer(dn_pre,x)
        grad["Un"]=np.outer(dn_pre,r*previous)
        grad["bn"]=dn_pre
        d_r=(p["Un"].T@dn_pre)*previous
        dr_pre=d_r*r*(1-r)
        grad["Wr"]=np.outer(dr_pre,x)
        grad["Ur"]=np.outer(dr_pre,previous)
        grad["br"]=dr_pre
        dz_pre=dz*z*(1-z)
        grad["Wz"]=np.outer(dz_pre,x)
        grad["Uz"]=np.outer(dz_pre,previous)
        grad["bz"]=dz_pre
        # Gradient stops at previous state: this is one-step truncated
        # training, not an unimplemented or falsely claimed full BPTT.
        return grad

    def update(self,cache,action,reward,rate=.016):
        grads=self.gradients(cache,action,reward)
        norm=math.sqrt(sum(float(np.sum(g*g)) for g in grads.values()))
        scale=min(1.,3./max(1e-12,norm))
        for key in self.params:
            self.params[key]-=rate*scale*grads[key]

def history_input(world,last_action,last_discovery,last_available):
    x=list(world.features())
    if len(x)!=16 or (last_action is not None and
                      (type(last_action)!=int or last_action not in range(SOURCES))):
        raise ValueError("invalid own history")
    onehot=[0.]*SOURCES
    if last_action is not None:onehot[last_action]=1.
    return np.array(x+onehot+[float(last_discovery),float(last_available)],dtype=float)

def train(seed,episodes):
    if type(seed)!=int or seed<0 or type(episodes)!=int or episodes<1:
        raise ValueError("invalid GRU training budget")
    model=GRU(seed)
    rng=np.random.default_rng(seed+77231)
    for ep in range(episodes):
        regime=TRAIN_REGIMES[ep%len(TRAIN_REGIMES)]
        rate=RATES[(ep//len(TRAIN_REGIMES))%len(RATES)]
        world_seed=2000000+seed*100000+ep
        world=FrozenWorld(make_timeline(world_seed,regime,rate))
        hidden=np.zeros(HIDDEN)
        last_action=None
        last_discovery=last_available=0
        epsilon=.08+.72*max(0.,1.-ep/max(1.,episodes*.8))
        for _ in range(HORIZON):
            x=history_input(world,last_action,last_discovery,last_available)
            values,next_hidden,cache=model.step(x,hidden)
            choice=(int(rng.integers(SOURCES)) if rng.random()<epsilon
                    else int(np.argmax(values)))
            reward,discovered=world.inspect(choice)
            # Only the selected observed outcome updates the model.
            model.update(cache,choice,float(discovered))
            hidden=next_hidden
            last_action=choice
            last_discovery=int(discovered)
            last_available=int(world.memory[choice]==1)
    return model

def replay(timeline,gru,mlp):
    result={}
    for arm in ARMS:
        world=FrozenWorld(timeline)
        hidden=np.zeros(HIDDEN)
        last_action=None
        last_discovery=last_available=0
        visits=[0]*SOURCES
        discoveries=0
        for _ in timeline["states"]:
            if arm=="scripted":choice=scripted(world)
            elif arm=="exploration_mlp":choice=learned(mlp,world)
            else:
                x=history_input(world,last_action,last_discovery,last_available)
                values,hidden,_=gru.step(x,hidden)
                choice=int(np.argmax(values))
            visits[choice]+=1
            reward,discovered=world.inspect(choice)
            discoveries+=int(discovered)
            last_action=choice
            last_discovery=int(discovered)
            last_available=int(world.memory[choice]==1)
        result[arm]={
            "direct_discoveries":discoveries,
            "distinct_sources":sum(x>0 for x in visits),
            "minimum_source_visits":min(visits)}
    return result

def benchmark(seeds=(11,17,23),episodes=180,heldout=30):
    if (not seeds or len(set(seeds))!=len(seeds)
        or any(type(s)!=int or s<0 for s in seeds)
        or type(episodes)!=int or episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid experiment specification")
    cases=[]
    for seed in seeds:
        gru=train(seed+101,episodes)
        mlp=train_exploration(seed+2,episodes)
        for regime_index,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                scores={arm:[] for arm in ARMS}
                diversity={arm:[] for arm in ARMS}
                hashes=[]
                for episode in range(heldout):
                    trajectory_seed=SEED_OFFSET+seed*100000+regime_index*10000+rate*1000+episode
                    timeline=make_timeline(trajectory_seed,regime,rate)
                    hashes.append(timeline["sha256"])
                    outcomes=replay(timeline,gru,mlp)
                    for arm in ARMS:
                        scores[arm].append(outcomes[arm]["direct_discoveries"])
                        diversity[arm].append(outcomes[arm]["minimum_source_visits"])
                cases.append({
                    "train_seed":seed,"regime":regime,
                    "updates_per_inspection":rate,"heldout_episodes":heldout,
                    "shared_trajectory_manifest_sha256":hashlib.sha256(canonical(hashes).encode()).hexdigest(),
                    "mean_direct_discoveries":{
                        arm:round(statistics.mean(scores[arm]),5) for arm in ARMS},
                    "mean_minimum_source_visits":{
                        arm:round(statistics.mean(diversity[arm]),5) for arm in ARMS},
                    "mean_vs_scripted":{
                        arm:round(statistics.mean(a-b for a,b in zip(scores[arm],scores["scripted"])),5)
                        for arm in ARMS if arm!="scripted"}})
    out={"schema":SCHEMA,"origin":"SIMULATED_ONLY",
         "training_seeds":list(seeds),"train_episodes_per_seed":episodes,
         "heldout_episodes_per_cell":heldout,
         "architecture":{"kind":"GRU","input_width":INPUT,"hidden_width":HIDDEN,
                         "action_count":SOURCES,
                         "training_gradient":"ONE_STEP_TRUNCATED_RECURRENT_GATE_GRADIENT"},
         "observations_are_selected_source_only":True,
         "policy_can_read_future_timeline":False,
         "training_uses_unselected_source_rewards":False,
         "matched_hidden_trajectories_per_episode":True,
         "real_forge_model_changed":False,
         "minecraft_model_promotion_authorized":False,
         "causal_superiority_claimed":False,
         "cases":cases}
    out["sha256"]=hashlib.sha256(canonical(out).encode()).hexdigest()
    return out

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",nargs="+",type=int,default=[11,17,23])
    p.add_argument("--episodes",type=int,default=180)
    p.add_argument("--heldout",type=int,default=30)
    p.add_argument("--output",type=Path,default=Path("recurrent-causal-attention.json"))
    a=p.parse_args()
    data=benchmark(tuple(a.seeds),a.episodes,a.heldout)
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    print("RECURRENT_CAUSAL_ATTENTION cases="+str(len(data["cases"]))+
          " live_model_unchanged=true")
if __name__=="__main__":
    main()
