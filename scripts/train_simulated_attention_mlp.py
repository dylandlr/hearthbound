#!/usr/bin/env python3
"""Experimental simulator-only selective-attention benchmark.

No Minecraft actions, LLM calls, trained policy deployment, or server data.
Each decision has a one-inspection budget; source truth is never in policy input.
Run: python3 scripts/train_simulated_attention_mlp.py --output attention-benchmark.json
"""
import argparse
import hashlib
import json
import math
import random
from pathlib import Path

SOURCES=4
FEATURES_PER_SOURCE=4
WIDTH=SOURCES*FEATURES_PER_SOURCE
HIDDEN=16
SCHEMA="hearthbound.simulated-selective-attention.v1"

class World:
    def __init__(self,seed):
        self.rng=random.Random(seed)
        self.volatility=[self.rng.uniform(.04,.46) for _ in range(SOURCES)]
        self.truth=[self.rng.randrange(2) for _ in range(SOURCES)]
        self.memory=[-1]*SOURCES
        self.ages=[20]*SOURCES
        self.step_count=0

    def features(self):
        # Only known/source-history information. Hidden truth is never included.
        x=[]
        for i in range(SOURCES):
            x.extend((float(self.memory[i]==-1),
                      float(self.memory[i]==1),
                      min(self.ages[i],20)/20.,
                      self.volatility[i]))
        return x

    def inspect(self,source):
        if not 0<=source<SOURCES: raise ValueError("invalid source")
        old=self.memory[source]
        current=self.truth[source]
        discovery=old==-1 or old!=current
        reward=(1.0 if discovery else 0.0)-.04
        for i in range(SOURCES):
            self.ages[i]=min(20,self.ages[i]+1)
        self.memory[source]=current
        self.ages[source]=0
        self.step_count+=1
        for i in range(SOURCES):
            if self.rng.random()<self.volatility[i]:
                self.truth[i]=1-self.truth[i]
        return reward,discovery

class MLP:
    def __init__(self,seed):
        rng=random.Random(seed)
        self.w1=[[rng.uniform(-.12,.12) for _ in range(WIDTH)] for _ in range(HIDDEN)]
        self.b1=[0.]*HIDDEN
        self.w2=[[rng.uniform(-.12,.12) for _ in range(HIDDEN)] for _ in range(SOURCES)]
        self.b2=[0.]*SOURCES

    def forward(self,x):
        if len(x)!=WIDTH or not all(math.isfinite(v) for v in x):
            raise ValueError("invalid observation")
        z=[sum(w*v for w,v in zip(row,x))+b for row,b in zip(self.w1,self.b1)]
        h=[max(0.,v) for v in z]
        y=[sum(w*v for w,v in zip(row,h))+b for row,b in zip(self.w2,self.b2)]
        return z,h,y

    def update(self,x,chosen,reward,rate=.012):
        z,h,y=self.forward(x)
        error=max(-2.,min(2.,y[chosen]-reward))
        old=self.w2[chosen][:]
        for k in range(HIDDEN):
            self.w2[chosen][k]-=rate*error*h[k]
        self.b2[chosen]-=rate*error
        for k in range(HIDDEN):
            delta=error*old[k] if z[k]>0 else 0.
            for j in range(WIDTH):
                self.w1[k][j]-=rate*delta*x[j]
            self.b1[k]-=rate*delta

def scripted(world):
    return max(range(SOURCES),key=lambda i:(world.ages[i],-i))

def learned(model,world):
    values=model.forward(world.features())[2]
    return max(range(SOURCES),key=lambda i:(values[i],-i))

def run_episode(seed,policy,horizon=32):
    world=World(seed)
    reward=0.
    discoveries=0
    for _ in range(horizon):
        action=policy(world)
        r,d=world.inspect(action)
        reward+=r
        discoveries+=int(d)
    return reward,discoveries

def evaluate(model,seed,count):
    results={}
    policies={
        "scripted_least_recent":scripted,
        "trained_mlp":lambda world:learned(model,world),
        "untrained_mlp":lambda world:learned(MLP(seed+999),world),
    }
    for name,policy in policies.items():
        total=0.
        discoveries=0
        for k in range(count):
            r,d=run_episode(90000000+seed*100000+k,policy)
            total+=r
            discoveries+=d
        results[name]={"mean_reward":round(total/count,5),
                       "mean_discoveries":round(discoveries/count,5),
                       "episodes":count,"inspections_per_episode":32}
    return results

def benchmark(seed=11,episodes=500,heldout=120):
    if episodes<1 or heldout<1:raise ValueError("episodes must be positive")
    model=MLP(seed)
    rng=random.Random(seed+7)
    for e in range(episodes):
        world=World(1000000+seed*100000+e)
        epsilon=.08+.75*max(0.,1.-e/max(1,episodes*.8))
        for _ in range(32):
            x=world.features()
            action=(rng.randrange(SOURCES) if rng.random()<epsilon
                    else learned(model,world))
            reward,_=world.inspect(action)
            model.update(x,action,reward)
    evaluation=evaluate(model,seed,heldout)
    report={
        "schema":SCHEMA,
        "origin":"SIMULATED_ONLY",
        "seed":seed,
        "training_episodes":episodes,
        "heldout_episodes":heldout,
        "observations_per_decision":1,
        "citizen_actions_authorized":False,
        "minecraft_learning_claimed":False,
        "minecraft_policy_deployed":False,
        "observation_width":WIDTH,
        "hidden_width":HIDDEN,
        "sources_per_episode":SOURCES,
        "evaluation":evaluation,
        "limitations":[
            "Synthetic stochastic resource changes, not Minecraft inventory outcomes",
            "No navigation, line-of-sight, communication, or task execution",
            "Volatility is supplied as a hypothetical known source feature",
            "Comparison is exploratory, not an independently validated learning claim"
        ]
    }
    payload=json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False)
    report["sha256"]=hashlib.sha256(payload.encode()).hexdigest()
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",type=int,default=11)
    parser.add_argument("--episodes",type=int,default=500)
    parser.add_argument("--heldout",type=int,default=120)
    parser.add_argument("--output",type=Path,default=Path("simulated-attention-benchmark.json"))
    args=parser.parse_args()
    report=benchmark(args.seed,args.episodes,args.heldout)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("SIMULATED_ATTENTION_BENCHMARK",json.dumps(report,sort_keys=True))

if __name__=="__main__":
    main()
