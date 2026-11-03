#!/usr/bin/env python3
"""Learned neural option controller for Hearthbound's fast colony simulator.

The upper 19->24->3 Q-network learns which *option* to run and when to
switch based on reward and previous-option memory. Option executors remain
predefined bounded primitives; no hand-coded option transition graph.
Minecraft controllers, observations and agent policy stay untouched.
"""
import argparse
import copy
import hashlib
import json
import math
import random
from pathlib import Path

import train_resource_task_switch as base
import ablate_resource_task_rewards as rewards
import evaluate_goal_memory_options as old

SCHEMA="hearthbound.learned-options.v1"
OPTIONS=("SEEK_WHEAT","SECONDARY_JOB","WAIT")
WIDTH=19
HIDDEN=24
GAMMA=0.96

class OptionQ:
    def __init__(self,seed):
        rng=random.Random(seed)
        self.w1=[[rng.uniform(-.13,.13) for _ in range(WIDTH)] for _ in range(HIDDEN)]
        self.b1=[0.]*HIDDEN
        self.w2=[[rng.uniform(-.13,.13) for _ in range(HIDDEN)] for _ in OPTIONS]
        self.b2=[0.]*len(OPTIONS)

    def values(self,x):
        if len(x)!=WIDTH or any(not math.isfinite(v) for v in x):
            raise ValueError("Invalid meta observation")
        z=[sum(a*b for a,b in zip(w,x))+bias for w,bias in zip(self.w1,self.b1)]
        h=[max(0.,v) for v in z]
        q=[sum(a*b for a,b in zip(w,h))+bias for w,bias in zip(self.w2,self.b2)]
        return z,h,q

    def update(self,x,a,target,rate=.011):
        z,h,q=self.values(x)
        error=max(-3.,min(3.,q[a]-target))
        old=self.w2[a][:]
        for i in range(HIDDEN):self.w2[a][i]-=rate*error*h[i]
        self.b2[a]-=rate*error
        for i in range(HIDDEN):
            dz=error*old[i] if z[i]>0 else 0.
            self.b1[i]-=rate*dz
            for j in range(WIDTH):self.w1[i][j]-=rate*dz*x[j]

class AgentHistory:
    """Only remembered decisions and returned task events, not hidden inventory."""
    def __init__(self):
        self.previous_option=None
        self.just_completed_secondary=False
        self.switches=0
        self.returned_to_primary=0
        self.history=[]

    def state(self,observation):
        if len(observation)!=base.N:raise ValueError("Wrong base observation schema")
        prev=tuple(float(self.previous_option==i) for i in range(len(OPTIONS)))
        return tuple(observation)+prev+(float(self.just_completed_secondary),)

    def register(self,option,event):
        if option not in range(len(OPTIONS)):
            raise ValueError("Invalid option")
        previous=self.previous_option
        if previous is not None and previous!=option:
            self.switches+=1
        if previous==1 and option==0 and self.just_completed_secondary:
            self.returned_to_primary+=1
        self.previous_option=option
        self.just_completed_secondary=(event=="OTHER_TASK_COMPLETE")
        self.history.append((option,event))

def mask(observation):
    mask_base=base.action_mask(observation)
    # Broad "seek wheat" option: inspect unknown source or haul observed
    # available wheat. The lower level action is never allowed to violate masks.
    seek=(bool(mask_base[2] or mask_base[3]) or
          observation[5]==1. or observation[10]==1.)
    return (seek,bool(mask_base[4]),bool(mask_base[5]))

def execute(option,observation,low_model):
    available=mask(observation)
    if not 0<=option<3 or not available[option]:
        raise ValueError("Illegal high-level option")
    if option==1:return 4
    if option==2:return 5
    low_mask=base.action_mask(observation)
    # This is the option's primitive implementation, not a learned high-level
    # option transition rule. Reward trains *when to choose* this option.
    candidates=[i for i in (2,3) if low_mask[i]]
    if not candidates:
        candidates=[i for i in (0,1)
                    if low_mask[i] and ((i==0 and observation[5]) or
                                        (i==1 and observation[10]))]
    if not candidates:
        candidates=[i for i in (0,1) if low_mask[i]]
    q=low_model.values(observation)[2]
    action=max(candidates,key=lambda i:q[i])
    if not low_mask[action]:raise AssertionError("Invalid primitive action")
    return action

def best(model,state,available):
    q=model.values(state)[2]
    return max((i for i,allowed in enumerate(available) if allowed),
               key=lambda i:q[i])

def train_meta(seed,low_model,episodes=480):
    if episodes<1:raise ValueError("No meta episodes")
    rng=random.Random(seed+120001)
    model=OptionQ(seed+120001)
    target=copy.deepcopy(model)
    replay=[]
    updates=0
    for ep in range(episodes):
        scenario=rewards.TRAIN_SCENARIOS[ep%len(rewards.TRAIN_SCENARIOS)]
        world=base.Colony(33000000+seed*100000+ep,scenario)
        history=AgentHistory()
        epsilon=.08+.8*max(0.,1.-ep/(.85*episodes))
        for _ in range(world.horizon):
            observation=world.vector()
            x=history.state(observation)
            available=mask(observation)
            permitted=[i for i,ok in enumerate(available) if ok]
            chosen=rng.choice(permitted) if rng.random()<epsilon else best(model,x,available)
            primitive=execute(chosen,observation,low_model)
            next_obs,reward,done,info=world.step(primitive)
            history.register(chosen,info["event"])
            nx=history.state(next_obs)
            # No scripted expert labels, no forced option changes and no
            # extra task-shaping reward: optimize existing colony+personal return.
            replay.append((x,chosen,reward,nx,done,mask(next_obs)))
            if len(replay)>5000:replay.pop(0)
            if len(replay)>=48:
                for before,a,r,after,terminal,allowed in rng.sample(replay,8):
                    bootstrap=0. if terminal else max(
                        value for value,ok in zip(target.values(after)[2],allowed) if ok)
                    model.update(before,a,r+GAMMA*bootstrap)
                    updates+=1
                if updates%1600==0:target=copy.deepcopy(model)
            if done:break
    return model,updates

def digest(model):
    payload={"schema":SCHEMA,"width":WIDTH,"hidden":HIDDEN,"options":OPTIONS,
             "origin":"SIMULATED_ONLY",
             "weights":{name:getattr(model,name) for name in ("w1","b1","w2","b2")}}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()

def rollout(meta,low,seed,scenario,policy,trace=False):
    world=base.Colony(seed,scenario)
    history=AgentHistory()
    events=[]
    personal=colony=0.
    for _ in range(world.horizon):
        observation=world.vector()
        if policy=="learned_options":
            option=best(meta,history.state(observation),mask(observation))
            primitive=execute(option,observation,low)
        elif policy=="frozen_neural":
            option=None
            primitive=base.greedy(low,observation)
        elif policy=="engineered_memory":
            if not hasattr(history,"engineered"):
                history.engineered=old.GoalMemory()
            primitive=old.choose(history.engineered,observation,low,world.steps)
            option=None
        elif policy=="scripted":
            option=None
            primitive=base.scripted(observation)
        else:raise ValueError("Unknown comparison policy")
        if not base.action_mask(observation)[primitive]:
            raise AssertionError("Selected masked primitive")
        _,_,done,info=world.step(primitive)
        if policy=="learned_options":
            history.register(option,info["event"])
        if policy=="engineered_memory":
            history.engineered.observe(info["event"],world.steps)
        personal+=info["personal_reward"]
        colony+=info["colony_reward"]
        if trace:
            events.append({"step":world.steps,
                           "option":OPTIONS[option] if option is not None else policy,
                           "primitive":base.ACTIONS[primitive],
                           "world_event":info["event"],
                           "source_observation_flags":list(observation[5:8])+list(observation[10:13]),
                           "secondary_completed":world.other_done})
        if done:break
    return {"flour_success":world.flour_done,
            "secondary_completed":world.other_done,
            "steps":world.steps,"invalid_requests":world.invalid_count,
            "personal_reward":round(personal,5),
            "colony_reward":round(colony,5),
            "option_switches":history.switches,
            "returns_after_secondary":history.returned_to_primary,
            "events":events}

def aggregate(episodes):
    n=len(episodes)
    return {"episodes":n,
            "flour_success":sum(e["flour_success"] for e in episodes),
            "flour_rate":round(sum(e["flour_success"] for e in episodes)/n,5),
            "secondary_completed":sum(e["secondary_completed"] for e in episodes),
            "invalid_requests":sum(e["invalid_requests"] for e in episodes),
            "option_switches":sum(e["option_switches"] for e in episodes),
            "returns_after_secondary":sum(e["returns_after_secondary"] for e in episodes),
            "mean_steps":round(sum(e["steps"] for e in episodes)/n,5),
            "colony_reward_per_episode":round(sum(e["colony_reward"] for e in episodes)/n,5),
            "personal_reward_per_episode":round(sum(e["personal_reward"] for e in episodes)/n,5)}

def benchmark(seeds=(11,13,17),low_episodes=350,meta_episodes=480,heldout=40):
    if not seeds or len(set(seeds))!=len(seeds) or min(low_episodes,meta_episodes,heldout)<1:
        raise ValueError("Invalid evaluation budget or duplicated seeds")
    results=[]
    for seed in seeds:
        low,_=rewards.train("goal_bonus",seed,low_episodes)
        low_hash=base.model_digest(low)
        meta,updates=train_meta(seed,low,meta_episodes)
        meta_hash=digest(meta)
        scenarios={}
        for i,name in enumerate(rewards.EVAL_SCENARIOS):
            first=700000000+i*1000000+seed*10000
            comparisons={}
            for policy in ("learned_options","frozen_neural","engineered_memory","scripted"):
                runs=[rollout(meta,low,first+j,name,policy) for j in range(heldout)]
                comparisons[policy]=aggregate(runs)
            comparisons["heldout_seed_start"]=first
            comparisons["learned_trace"]=rollout(meta,low,first,name,"learned_options",trace=True)
            scenarios[name]=comparisons
        if digest(meta)!=meta_hash or base.model_digest(low)!=low_hash:
            raise AssertionError("Frozen network changed during evaluation")
        results.append({"seed":seed,"meta_updates":updates,
                        "meta_sha256":meta_hash,"low_sha256":low_hash,
                        "models_frozen":True,"scenarios":scenarios})
    return {"schema":SCHEMA,"primitive_observation_schema":base.SCHEMA,
            "meta_input_width":WIDTH,"meta_hidden_width":HIDDEN,
            "option_actions":list(OPTIONS),
            "meta_option_selection_learned":True,
            "option_switching_learned_from_reward":True,
            "option_primitive_executors":"HAND_DESIGNED_BOUNDED",
            "goal_memory":"LAST_OPTION_AND_LAST_SECONDARY_EVENT",
            "recurrent_network_trained":False,
            "training_origin":"SIMULATED_ONLY","evaluation_origin":"SIMULATED_ONLY",
            "minecraft_worlds":0,"minecraft_execution_authorized":False,
            "heldout_episodes_per_scenario_seed":heldout,
            "results":results,
            "limitations":[
                "Option choices/switches are learned from TD reward; option execution is still manually bounded",
                "Memory is one-step explicit history, not LSTM/GRU or persistent Minecraft NBT",
                "Source availability is local and partially observed; resource dynamics are synthetic",
                "No multi-citizen scheduling, interrupts from true Minecraft, or action authorization",
            ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--meta-episodes",type=int,default=480)
    p.add_argument("--low-episodes",type=int,default=350)
    p.add_argument("--heldout",type=int,default=40)
    p.add_argument("--output",type=Path,default=Path("learned-options.json"))
    a=p.parse_args()
    data=benchmark(low_episodes=a.low_episodes,meta_episodes=a.meta_episodes,heldout=a.heldout)
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    for row in data["results"]:
        for name,case in row["scenarios"].items():
            print("LEARNED_OPTIONS_SIM seed="+str(row["seed"]),"scenario="+name,
                  "learned="+str(case["learned_options"]["flour_rate"]),
                  "engineered="+str(case["engineered_memory"]["flour_rate"]),
                  "scripted="+str(case["scripted"]["flour_rate"]),
                  "frozen="+str(case["frozen_neural"]["flour_rate"]),
                  "switches="+str(case["learned_options"]["option_switches"]))
    print("LEARNED_OPTIONS_COMPLETE minecraft_worlds=0")
if __name__=="__main__":main()
