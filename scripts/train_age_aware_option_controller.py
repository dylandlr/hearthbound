#!/usr/bin/env python3
"""Age-aware learned options with explicit sensory refresh in a fast simulator.

New 21->24->4 upper-level Q model; frozen v0.10.4 controller is a baseline.
No new Minecraft observation or action is installed. The refresh primitive is
SIMULATED_ONLY and consumes a real environment step; it is not privileged
inventory access or a free synchronization of the world.
"""
import argparse
import copy
import hashlib
import json
import math
import random
from collections import deque
from pathlib import Path

import train_resource_task_switch as base
import ablate_resource_task_rewards as reward
import train_learned_option_controller as v4
import evaluate_option_interruption_stress as stress

SCHEMA="hearthbound.age-aware-options.v1"
OPTIONS=("SEEK_WHEAT","SECONDARY_JOB","WAIT","REFRESH_SENSORS")
INPUT=21
HIDDEN=24
GAMMA=.96
TRAIN_PROFILES=(
    {"horizon":28,"delay":0,"interrupt_every":0},
    {"horizon":28,"delay":2,"interrupt_every":0},
    {"horizon":28,"delay":4,"interrupt_every":0},
    {"horizon":28,"delay":0,"interrupt_every":4},
    {"horizon":42,"delay":3,"interrupt_every":5},
)
TRAIN_SCENARIOS=reward.TRAIN_SCENARIOS
# No world from the stress holdout or earlier evaluation is used for training.

class Network:
    def __init__(self,seed):
        r=random.Random(seed)
        self.w1=[[r.uniform(-.13,.13) for _ in range(INPUT)] for _ in range(HIDDEN)]
        self.b1=[0.]*HIDDEN
        self.w2=[[r.uniform(-.13,.13) for _ in range(HIDDEN)] for _ in OPTIONS]
        self.b2=[0.]*len(OPTIONS)
    def values(self,x):
        if len(x)!=INPUT or any(not math.isfinite(v) for v in x):
            raise ValueError("Invalid age-aware feature vector")
        z=[sum(a*b for a,b in zip(w,x))+b for w,b in zip(self.w1,self.b1)]
        h=[max(0.,v) for v in z]
        return z,h,[sum(a*b for a,b in zip(w,h))+b for w,b in zip(self.w2,self.b2)]
    def update(self,x,action,target,rate=.011):
        if not 0<=action<len(OPTIONS):
            raise ValueError("Invalid learned action")
        z,h,q=self.values(x)
        error=max(-3.,min(3.,q[action]-target))
        previous=self.w2[action][:]
        for i in range(HIDDEN):self.w2[action][i]-=rate*error*h[i]
        self.b2[action]-=rate*error
        for i in range(HIDDEN):
            delta=error*previous[i] if z[i]>0 else 0.
            self.b1[i]-=rate*delta
            for j in range(INPUT):self.w1[i][j]-=rate*delta*x[j]

class Memory:
    def __init__(self):
        self.previous_option=None
        self.secondary_event=False
        self.switches=0
    def encode(self,observation,age):
        if len(observation)!=base.N or age<0:
            raise ValueError("Invalid sensor state or age")
        option=tuple(float(self.previous_option==i) for i in range(len(OPTIONS)))
        return tuple(observation)+option+(float(self.secondary_event),min(age,8)/8)
    def register(self,choice,event):
        if self.previous_option is not None and choice!=self.previous_option:
            self.switches+=1
        self.previous_option=choice
        self.secondary_event=event=="OTHER_TASK_COMPLETE"

class DelayedWorld:
    """Observation transport with explicit, costly local-refresh requests.

    Refresh is not a Minecraft action. It advances a WAIT world tick, then
    obtains a fresh *post-tick* sensor snapshot for the NEXT decision.
    A separate supervisor may validate current-state legality but may not
    disclose its observations to the learned action selection.
    """
    def __init__(self,seed,scenario,profile):
        self.world=base.Colony(seed,scenario,horizon=profile["horizon"])
        self.delay=profile["delay"]
        self.interrupt_every=profile["interrupt_every"]
        if self.delay<0 or self.interrupt_every<0:
            raise ValueError("Invalid delay configuration")
        self.samples=deque()
        self.forced_current=None
        self.last_sample_step=None
        self.last_sample=None
        self.memory=Memory()
        self.rejections=0
        self.refreshes=0
        self.interruptions=0
        self.personal=0.
        self.colony=0.
        self.events=[]
    def sense(self):
        if self.last_sample_step==self.world.steps:
            sample=self.last_sample
            return sample[1],self.world.steps-sample[0]
        # A sample has an immutable collection step; age is public to
        # the controller, whereas current inventory remains supervisor-only.
        if self.forced_current is not None:
            sample=self.forced_current
            self.forced_current=None
        else:
            self.samples.append((self.world.steps,self.world.vector()))
            sample=self.samples[max(0,len(self.samples)-1-self.delay)]
        self.last_sample_step=self.world.steps
        self.last_sample=sample
        age=self.world.steps-sample[0]
        return sample[1],age
    def act(self,choice,low,obs,age,record=False):
        if choice not in range(len(OPTIONS)):
            raise ValueError("Invalid option index")
        interrupted=bool(self.interrupt_every and
                         (self.world.steps+1)%self.interrupt_every==0)
        if interrupted:
            action=5
            event_option="INTERRUPTED"
            self.interruptions+=1
        elif choice==3:
            action=5
            event_option="REFRESH_SENSORS"
            self.refreshes+=1
        elif choice==2:
            action=5
            event_option="WAIT"
        elif choice==1:
            action=4
            event_option="SECONDARY_JOB"
        else:
            action=v4.execute(0,obs,low)
            event_option="SEEK_WHEAT"
        if not base.action_mask(self.world.vector())[action]:
            action=5
            self.rejections+=1
            event_option+=":REJECTED"
        _,r,done,info=self.world.step(action)
        self.personal+=info["personal_reward"]
        self.colony+=info["colony_reward"]
        if not interrupted:
            self.memory.register(choice,info["event"])
        if choice==3 and not interrupted:
            # Refresh reads only after the tick; no hidden state is passed
            # into the current action and refresh may fail if interrupted.
            self.forced_current=(self.world.steps,self.world.vector())
        if record:
            self.events.append({
                "step":self.world.steps,"age":age,"chosen_option":OPTIONS[choice],
                "executed":base.ACTIONS[action],"result":info["event"],
                "supervisor_rejected":event_option.endswith(":REJECTED"),
                "interrupted":interrupted,
                "refresh_requested":choice==3,
            })
        return r,done,info

def option_mask(observation):
    low=v4.mask(observation)
    return (low[0],low[1],low[2],True)

def select(model,x,allowed):
    q=model.values(x)[2]
    return max((i for i,v in enumerate(allowed) if v),key=lambda i:q[i])

def train(seed,low,episodes=520):
    if episodes<1:raise ValueError("No training episodes")
    r=random.Random(seed+650000)
    online=Network(seed+650000)
    target=copy.deepcopy(online)
    replay=[]
    updates=0
    for ep in range(episodes):
        profile=TRAIN_PROFILES[ep%len(TRAIN_PROFILES)]
        scenario=TRAIN_SCENARIOS[(ep//len(TRAIN_PROFILES))%len(TRAIN_SCENARIOS)]
        world=DelayedWorld(44000000+seed*100000+ep,scenario,profile)
        epsilon=.08+.8*max(0.,1.-ep/(episodes*.85))
        for _ in range(world.world.horizon):
            observed,age=world.sense()
            x=world.memory.encode(observed,age)
            valid=option_mask(observed)
            options=[i for i,v in enumerate(valid) if v]
            action=r.choice(options) if r.random()<epsilon else select(online,x,valid)
            rejected_before=world.rejections
            reward_total,done,_=world.act(action,low,observed,age)
            # Penalize rejected stale proposals only in the TD training target.
            # The original environment's personal/colony reward stays intact.
            penalty=.18 if world.rejections>rejected_before else 0.
            nx_observed,nx_age=world.sense()
            nx=world.memory.encode(nx_observed,nx_age)
            next_mask=option_mask(nx_observed)
            replay.append((x,action,reward_total-penalty,nx,done,next_mask))
            if len(replay)>6000:replay.pop(0)
            if len(replay)>=48:
                for before,a,rew,after,terminal,allowed in r.sample(replay,8):
                    v=0. if terminal else max(q for q,ok in
                        zip(target.values(after)[2],allowed) if ok)
                    online.update(before,a,rew+GAMMA*v)
                    updates+=1
                if updates%1600==0:target=copy.deepcopy(online)
            if done:break
    return online,updates

def digest(model):
    d={"schema":SCHEMA,"input_width":INPUT,"hidden_width":HIDDEN,
       "options":OPTIONS,"training_origin":"SIMULATED_ONLY",
       "weights":{x:getattr(model,x) for x in ("w1","b1","w2","b2")}}
    return hashlib.sha256(json.dumps(d,sort_keys=True,allow_nan=False).encode()).hexdigest()

def evaluate_age(model,low,seed,scenario,profile,trace=False):
    w=DelayedWorld(seed,scenario,profile)
    for _ in range(w.world.horizon):
        obs,age=w.sense()
        action=select(model,w.memory.encode(obs,age),option_mask(obs))
        w.act(action,low,obs,age,record=trace)
        if w.world.finished:break
    return {"flour_success":w.world.flour_done,"secondary_done":w.world.other_done,
            "steps":w.world.steps,"invalid_requests":w.world.invalid_count,
            "safety_rejections":w.rejections,"refreshes":w.refreshes,
            "interruptions":w.interruptions,"option_switches":w.memory.switches,
            "personal_reward":round(w.personal,5),
            "colony_reward":round(w.colony,5),"trace":w.events}

def aggregate(rows):
    n=len(rows)
    return {
        "episodes":n,
        "successes":sum(v["flour_success"] for v in rows),
        "success_rate":round(sum(v["flour_success"] for v in rows)/n,5),
        "safety_rejections":sum(v["safety_rejections"] for v in rows),
        "valid_proposal_rate":round(
            1-sum(v["safety_rejections"] for v in rows)/
            max(1,sum(v["steps"]-v["interruptions"] for v in rows)),5),
        "refreshes":sum(v["refreshes"] for v in rows),
        "interruptions":sum(v["interruptions"] for v in rows),
        "invalid_requests":sum(v["invalid_requests"] for v in rows),
        "mean_steps":round(sum(v["steps"] for v in rows)/n,5),
        "colony_reward":round(sum(v["colony_reward"] for v in rows)/n,5),
        "personal_reward":round(sum(v["personal_reward"] for v in rows)/n,5),
    }

def benchmark(seeds=(11,13,17),low_episodes=350,old_episodes=480,
              age_episodes=520,heldout=30):
    if not seeds or len(set(seeds))!=len(seeds) or min(
        low_episodes,old_episodes,age_episodes,heldout)<1:
        raise ValueError("Bad training/evaluation budgets")
    result=[]
    for seed in seeds:
        low,_=reward.train("goal_bonus",seed,low_episodes)
        old,_=v4.train_meta(seed,low,old_episodes)
        aged,updates=train(seed,low,age_episodes)
        low_hash=base.model_digest(low)
        old_hash=v4.digest(old)
        aged_hash=digest(aged)
        cases={}
        for i,(profile_name,profile) in enumerate(stress.STRESS.items()):
            profile_cases={}
            for j,scenario in enumerate(stress.SCENARIOS):
                start=950000000+seed*100000+i*10000+j*1000
                new=[evaluate_age(aged,low,start+k,scenario,profile)
                     for k in range(heldout)]
                control=[stress.replay(old,low,start+k,scenario,
                                       "learned_options",profile)
                         for k in range(heldout)]
                profile_cases[scenario]={
                    "seed_start":start,
                    "age_aware":aggregate(new),
                    "frozen_legacy":stress.aggregate(control),
                    "trace":evaluate_age(aged,low,start,scenario,profile,True)["trace"],
                }
            cases[profile_name]=profile_cases
        if (base.model_digest(low)!=low_hash or v4.digest(old)!=old_hash or
                digest(aged)!=aged_hash):
            raise AssertionError("Weights changed during heldout evaluation")
        result.append({"seed":seed,"age_updates":updates,
                       "age_sha256":aged_hash,"legacy_sha256":old_hash,
                       "low_sha256":low_hash,"models_frozen":True,
                       "profiles":cases})
    return {
        "schema":SCHEMA,"network":"21-24-4",
        "features":"15 source/task + 4 previous-option + 1 last-secondary-event + 1 observation-age",
        "option_actions":OPTIONS,"sensor_refresh":"SIMULATED_ONLY_ONE_WORLD_TICK",
        "model_training":"SIMULATED_ONLY",
        "evaluation_data":"SIMULATED_ONLY",
        "minecraft_worlds":0,"minecraft_execution_authorized":False,
        "observations_fully_fresh_for_policy":False,
        "supervisor_current_state_only_for_safety":True,
        "results":result,"heldout_episodes_per_cell":heldout,
        "limitations":[
            "Refresh option is an abstract sensor request, not a Minecraft command",
            "Base simulator resource quantities are unchanged and not Minecraft-calibrated",
            "Safety supervisor remains active; report its interventions independently",
            "Trained and evaluated delayed regimes share profile parameters; episode seeds are disjoint",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--low-episodes",type=int,default=350)
    p.add_argument("--old-episodes",type=int,default=480)
    p.add_argument("--age-episodes",type=int,default=520)
    p.add_argument("--heldout",type=int,default=30)
    p.add_argument("--output",type=Path,default=Path("age-aware-options.json"))
    a=p.parse_args()
    report=benchmark(low_episodes=a.low_episodes,old_episodes=a.old_episodes,
                     age_episodes=a.age_episodes,heldout=a.heldout)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    for profile in stress.STRESS:
        for scenario in stress.SCENARIOS:
            rows=[r["profiles"][profile][scenario] for r in report["results"]]
            learned=sum(r["age_aware"]["success_rate"] for r in rows)/len(rows)
            older=sum(r["frozen_legacy"]["flour_rate"] for r in rows)/len(rows)
            rejection=sum(r["age_aware"]["safety_rejections"] for r in rows)
            previous=sum(r["frozen_legacy"]["safety_rejections"] for r in rows)
            refresh=sum(r["age_aware"]["refreshes"] for r in rows)
            print("AGE_AWARE_STRESS",profile,scenario,
                  "new="+str(round(learned,4)),"legacy="+str(round(older,4)),
                  "new_rejections="+str(rejection),"legacy_rejections="+str(previous),
                  "refreshes="+str(refresh))
    print("AGE_AWARE_SIMULATED_ONLY minecraft_worlds=0")
if __name__=="__main__": main()
