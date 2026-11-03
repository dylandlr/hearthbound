#!/usr/bin/env python3
"""Small reproducible *simulated* DQN-like neural Q-learning benchmark.

Minecraft remains the authoritative evaluation world. This deliberately
abstract environment provides varied observable shortage decisions; its
rollouts must never be represented as real Minecraft experience.
No pretrained scripted labels, LLM calls, or inherited Minecraft recipes.
"""
import argparse
import copy
import json
import math
import random
from pathlib import Path

SCHEMA="hearthbound.mill-observation.v2"
FEATURES=("powered","mill_wheat_present","mill_flour_present","mill_blocked",
          "verified_experience_norm","source_unknown","source_empty",
          "source_available","task_active","source_stale")
ACTIONS=("INSPECT_SOURCE","WAIT_FOR_SUPPLY","REQUEST_WHEAT_HAUL")
WIDTH=10
HIDDEN=20

class World:
    def __init__(self, seed, horizon=16):
        self.rng=random.Random(seed)
        self.horizon=horizon
        self.supply=self.rng.random()<0.45
        self.known="UNKNOWN"
        self.age=0
        self.steps=0
        self.finished=False

    def state(self):
        known="UNKNOWN" if self.age>100 and self.known!="UNKNOWN" else self.known
        return (1.,0.,0.,0.,0.,
                float(known=="UNKNOWN"),float(known=="EMPTY"),
                float(known=="AVAILABLE"),0.,
                float(self.age>100 and self.known!="UNKNOWN"))

    def step(self, action):
        if self.finished or action not in ACTIONS:
            raise ValueError("Invalid episode action")
        self.steps+=1
        colony=-0.02
        personal=0.
        invalid=False
        if action=="INSPECT_SOURCE":
            # Sensor reveals local resource; does not generate a resource.
            self.known="AVAILABLE" if self.supply else "EMPTY"
            self.age=0
        elif action=="WAIT_FOR_SUPPLY":
            # Exogenous supply restock, not citizen discovery/production.
            if not self.supply and self.rng.random()<0.30:
                self.supply=True
                self.known="UNKNOWN"
            self.age+=40
        else:
            if self.supply and self.known=="AVAILABLE" and self.age<=100:
                colony+=1.0
                personal+=1.0
                self.supply=False
                self.finished=True
            else:
                colony-=0.15
                invalid=True
            self.age+=40
        timeout=self.steps>=self.horizon
        self.finished=self.finished or timeout
        return self.state(),round(colony+personal,6),self.finished,{
            "colony":round(colony,6),"personal":personal,
            "invalid_request":invalid,"success":personal==1.,
            "timeout":timeout and personal!=1.
        }

class NeuralQ:
    """10 -> 20 ReLU -> 3 value approximator, explicit online SGD backprop."""
    def __init__(self, seed):
        rng=random.Random(seed)
        self.w1=[[rng.uniform(-0.15,0.15) for _ in range(WIDTH)]
                 for _ in range(HIDDEN)]
        self.b1=[0.]*HIDDEN
        self.w2=[[rng.uniform(-0.15,0.15) for _ in range(HIDDEN)]
                 for _ in ACTIONS]
        self.b2=[0.]*len(ACTIONS)

    def values(self, x):
        if len(x)!=WIDTH or not all(math.isfinite(v) for v in x):
            raise ValueError("Invalid observation feature vector")
        z=[sum(a*b for a,b in zip(w,x))+bias
           for w,bias in zip(self.w1,self.b1)]
        h=[max(0.,v) for v in z]
        q=[sum(a*b for a,b in zip(w,h))+bias
           for w,bias in zip(self.w2,self.b2)]
        return z,h,q

    def train_one(self, x, action_idx, target, lr=0.012):
        z,h,q=self.values(x)
        error=max(-4.,min(4.,q[action_idx]-target))
        old=list(self.w2[action_idx])
        for i in range(HIDDEN):
            self.w2[action_idx][i]-=lr*error*h[i]
        self.b2[action_idx]-=lr*error
        for i in range(HIDDEN):
            dz=error*old[i] if z[i]>0 else 0.
            for j in range(WIDTH):
                self.w1[i][j]-=lr*dz*x[j]
            self.b1[i]-=lr*dz

def best(q):
    return max(range(len(q)), key=lambda i:q[i])

def scripted(s):
    if s[5]:return 0
    if s[6]:return 1
    return 2

def evaluate(policy, seeds):
    totals={"episodes":0,"successes":0,"timeouts":0,"invalid_requests":0,
            "steps":0,"colony_reward":0.,"personal_reward":0.}
    for seed in seeds:
        env=World(seed)
        for _ in range(env.horizon):
            action=policy(env.state())
            _,_,done,info=env.step(ACTIONS[action])
            totals["steps"]+=1
            totals["invalid_requests"]+=int(info["invalid_request"])
            totals["colony_reward"]+=info["colony"]
            totals["personal_reward"]+=info["personal"]
            totals["successes"]+=int(info["success"])
            totals["timeouts"]+=int(info["timeout"])
            if done:break
        totals["episodes"]+=1
    totals["success_rate"]=round(totals["successes"]/totals["episodes"],4)
    totals["mean_steps"]=round(totals["steps"]/totals["episodes"],4)
    for field in ("colony_reward","personal_reward"):
        totals[field]=round(totals[field]/totals["episodes"],4)
    return totals

def train(seed=11,episodes=2400):
    rng=random.Random(seed)
    model=NeuralQ(seed)
    target=copy.deepcopy(model)
    replay=[]
    updates=0
    for episode in range(episodes):
        env=World(1000000+seed*100000+episode)
        epsilon=0.08+0.82*max(0.,1.-episode/max(1,episodes*.75))
        for _ in range(env.horizon):
            x=env.state()
            idx=rng.randrange(len(ACTIONS)) if rng.random()<epsilon else best(model.values(x)[2])
            nx,reward,done,_=env.step(ACTIONS[idx])
            replay.append((x,idx,reward,nx,done))
            if len(replay)>10000:replay.pop(0)
            if len(replay)>=48:
                for ox,a,r,after,terminal in rng.sample(replay,16):
                    bootstrap=0. if terminal else max(target.values(after)[2])
                    model.train_one(ox,a,r+0.95*bootstrap)
                    updates+=1
                if updates//16%100==0:
                    target=copy.deepcopy(model)
            if done:break
    return model,updates

def benchmark(seed=11,episodes=2400,heldout=400):
    if episodes<1 or heldout<1:raise ValueError("Need positive episodes and evaluation count")
    model,updates=train(seed,episodes)
    # All evaluation seeds are disjoint from simulator training seeds.
    seeds=[90000000+seed*100000+i for i in range(heldout)]
    learned=evaluate(lambda x:best(model.values(x)[2]),seeds)
    baseline=evaluate(scripted,seeds)
    random_policy_rng=random.Random(seed+700)
    untrained=NeuralQ(seed+900)
    random_baseline=evaluate(lambda x:best(untrained.values(x)[2]),seeds)
    return {
      "schema":"hearthbound.simulated-mill-neural-q.v1",
      "observation_schema":SCHEMA,
      "feature_names":list(FEATURES),
      "actions":list(ACTIONS),
      "train_episodes":episodes,"heldout_episodes":heldout,
      "seed":seed,"gradient_updates":updates,
      "environment":"abstract fast simulated wheat availability",
      "training_data_origin":"SIMULATED_ONLY",
      "minecraft_execution_claimed":False,
      "minecraft_learning_claimed":False,
      "evaluation":{"neural_q":learned,"scripted_reference":baseline,
                    "untrained_network":random_baseline},
      "limits":["only one abstract resource and mill; no navigation or Create physics",
                "not tested for generalization in Minecraft",
                "fixed policy and reward metrics from synthetic environment"]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seed",type=int,default=11)
    p.add_argument("--episodes",type=int,default=2400)
    p.add_argument("--heldout",type=int,default=400)
    p.add_argument("--output",type=Path,default=Path("simulated-neural-q-results.json"))
    a=p.parse_args()
    result=benchmark(a.seed,a.episodes,a.heldout)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print(json.dumps(result,indent=2,sort_keys=True))
if __name__=="__main__":main()
