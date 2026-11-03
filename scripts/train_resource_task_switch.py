#!/usr/bin/env python3
"""Two-source + alternate-occupation partially observed neural-Q experiment.

SIMULATOR ONLY: resources and jobs are abstract, not Minecraft controls.
New model and observation schema; the verified v2 neural baseline is frozen.
"""
import argparse
import copy
import hashlib
import json
import math
import random
from pathlib import Path

SCHEMA="hearthbound.resource-task-observation.v1"
FEATURES=(
    "mill_powered","mill_wheat","mill_flour","mill_blocked","experience_norm",
    "primary_unknown","primary_empty","primary_available","task_active","primary_stale",
    "alternate_unknown","alternate_empty","alternate_available",
    "other_job_available","other_job_done",
)
ACTIONS=("INSPECT_PRIMARY","INSPECT_ALTERNATE","HAUL_PRIMARY",
         "HAUL_ALTERNATE","DO_OTHER_JOB","WAIT")
N,H=len(FEATURES),24
assert N==15 and len(ACTIONS)==6
SOURCES=("primary","alternate")

class Colony:
    """Finite supplies; inspections reveal only a local source, never magically restock."""
    def __init__(self, seed, scenario="standard", horizon=14):
        if scenario not in ("standard","primary_empty","both_empty","alternate_empty",
                            "no_secondary_job","supply_shift"):
            raise ValueError("Unknown scenario")
        r=self.rng=random.Random(seed)
        self.scenario=scenario
        self.horizon=horizon
        self.supply={
            "primary": int(r.random()<0.45),
            "alternate": int(r.random()<0.65),
        }
        self.other_available=r.random()<0.8
        if scenario=="primary_empty": self.supply["primary"]=0;self.supply["alternate"]=1
        if scenario=="both_empty": self.supply={"primary":0,"alternate":0}
        if scenario=="alternate_empty":self.supply["alternate"]=0
        if scenario=="no_secondary_job":self.other_available=False
        if scenario=="supply_shift":self.supply["primary"]=0;self.supply["alternate"]=1
        self.knowledge={name:"UNKNOWN" for name in SOURCES}
        self.observed_age={name:0 for name in SOURCES}
        self.other_done=False
        self.flour_done=False
        self.steps=0
        self.finished=False
        self.invalid_count=0
        self.events=[]

    def observed(self, source):
        if self.knowledge[source]!="UNKNOWN" and self.observed_age[source]>3:
            return "UNKNOWN",True
        return self.knowledge[source],False

    def vector(self):
        p,stale_p=self.observed("primary")
        a,_=self.observed("alternate")
        return (1.,0.,0.,0.,0.,
                float(p=="UNKNOWN"),float(p=="EMPTY"),float(p=="AVAILABLE"),
                0.,float(stale_p),
                float(a=="UNKNOWN"),float(a=="EMPTY"),float(a=="AVAILABLE"),
                float(self.other_available and not self.other_done),
                float(self.other_done))

    def step(self, index):
        if self.finished or not isinstance(index,int) or not 0<=index<len(ACTIONS):
            raise ValueError("Illegal episode action")
        action=ACTIONS[index]
        self.steps+=1
        colony=-0.02
        personal=0.
        invalid=False
        event="WAITED"
        if action in ("INSPECT_PRIMARY","INSPECT_ALTERNATE"):
            which="primary" if action=="INSPECT_PRIMARY" else "alternate"
            self.knowledge[which]="AVAILABLE" if self.supply[which]>0 else "EMPTY"
            self.observed_age[which]=0
            event="INSPECTED_"+which.upper()
        elif action in ("HAUL_PRIMARY","HAUL_ALTERNATE"):
            which="primary" if action=="HAUL_PRIMARY" else "alternate"
            state,stale=self.observed(which)
            if not self.flour_done and self.supply[which]>0 and state=="AVAILABLE" and not stale:
                self.supply[which]-=1
                self.flour_done=True
                colony+=1.0
                personal+=0.6
                event="FLOUR_TASK_COMPLETE"
            else:
                invalid=True
                colony-=0.2
                event="DENIED_HAUL"
        elif action=="DO_OTHER_JOB":
            if self.other_available and not self.other_done:
                self.other_done=True
                colony+=0.40
                personal+=0.35
                event="OTHER_TASK_COMPLETE"
            else:
                invalid=True
                colony-=0.2
                event="DENIED_OTHER_JOB"
        else:
            # Waiting does not give guaranteed free wheat; the "supply_shift"
            # scenario forces a primary stock transition before a stale read.
            if self.scenario=="supply_shift" and self.steps==3:
                self.supply["primary"]=1
                event="EXOGENOUS_PRIMARY_RESTOCK"
            elif self.rng.random()<0.12:
                self.supply["primary"]=1
                event="EXOGENOUS_PRIMARY_RESTOCK"
        for source in SOURCES:
            if action!=("INSPECT_PRIMARY" if source=="primary" else "INSPECT_ALTERNATE"):
                self.observed_age[source]+=1
        self.invalid_count+=int(invalid)
        self.finished=self.flour_done or self.steps>=self.horizon
        info={
            "event":event,"personal_reward":round(personal,5),
            "colony_reward":round(colony,5),"invalid":invalid,
            "flour_success":self.flour_done,"other_job_success":self.other_done,
            "timeout":self.finished and not self.flour_done,
        }
        self.events.append({"step":self.steps,"action":action,**info})
        return self.vector(),round(personal+colony,5),self.finished,info

def action_mask(obs):
    if len(obs)!=N or any(not math.isfinite(x) or x<0 or x>1 for x in obs):
        raise ValueError("Bad observation")
    if sum(obs[5:8])!=1. or sum(obs[10:13])!=1.:
        raise ValueError("Invalid partial-resource knowledge")
    if obs[9] and obs[5]!=1.:raise ValueError("Stale source was not masked unknown")
    if obs[0]!=1 or obs[1]!=0 or obs[2]!=0 or obs[3]!=0 or obs[8]!=0:
        return (False,False,False,False,False,True)
    # A sensor can be inspected anytime, but physical hauling requires
    # known, nonstale wheat and other jobs require actual observed availability.
    return (True,True,obs[7]==1. and obs[9]==0.,
            obs[12]==1.,obs[13]==1. and obs[14]==0.,True)

class QNetwork:
    def __init__(self,seed):
        r=random.Random(seed)
        self.w1=[[r.uniform(-0.13,0.13) for _ in range(N)] for _ in range(H)]
        self.b1=[0.]*H
        self.w2=[[r.uniform(-0.13,0.13) for _ in range(H)] for _ in ACTIONS]
        self.b2=[0.]*len(ACTIONS)

    def values(self,x):
        if len(x)!=N:raise ValueError("Invalid feature count")
        z=[sum(a*b for a,b in zip(w,x))+bias for w,bias in zip(self.w1,self.b1)]
        h=[max(0.,v) for v in z]
        return z,h,[sum(a*b for a,b in zip(w,h))+bias
                    for w,bias in zip(self.w2,self.b2)]

    def update(self,x,action,target,rate=0.009):
        z,h,q=self.values(x)
        err=max(-3.,min(3.,q[action]-target))
        old=self.w2[action][:]
        for k in range(H):self.w2[action][k]-=rate*err*h[k]
        self.b2[action]-=rate*err
        for k in range(H):
            dz=err*old[k] if z[k]>0 else 0.
            self.b1[k]-=rate*dz
            for j in range(N):self.w1[k][j]-=rate*dz*x[j]

def greedy(model,obs):
    mask=action_mask(obs)
    q=model.values(obs)[2]
    return max((idx for idx,valid in enumerate(mask) if valid),key=lambda i:q[i])

def scripted(obs):
    mask=action_mask(obs)
    if mask[2]:return 2
    if mask[3]:return 3
    if obs[5]:return 0
    if obs[10]:return 1
    if mask[4]:return 4
    return 5

def train(seed,episodes):
    if episodes<1:raise ValueError("No training episodes")
    rng=random.Random(seed)
    online=QNetwork(seed)
    target=copy.deepcopy(online)
    replay=[]
    updates=0
    decisions=0
    for episode in range(episodes):
        world=Colony(10000000+seed*100000+episode,
                     scenario=("standard","primary_empty","both_empty",
                               "alternate_empty","no_secondary_job")[episode%5])
        epsilon=0.07+0.83*max(0.,1.-episode/(episodes*.8))
        for _ in range(world.horizon):
            obs=world.vector()
            valid=[i for i,allowed in enumerate(action_mask(obs)) if allowed]
            move=rng.choice(valid) if rng.random()<epsilon else greedy(online,obs)
            nxt,reward,done,_=world.step(move)
            replay.append((obs,move,reward,nxt,done))
            if len(replay)>6000:replay.pop(0)
            if len(replay)>=48:
                for x,a,r,nx,terminal in rng.sample(replay,12):
                    allowed=action_mask(nx)
                    future=0. if terminal else max(q for q,ok in zip(target.values(nx)[2],allowed) if ok)
                    online.update(x,a,r+0.96*future)
                    updates+=1
                if updates%1200==0:target=copy.deepcopy(online)
            decisions+=1
            if done:break
    return online,{"updates":updates,"decisions":decisions}

def evaluate(policy,seed,scenario,count):
    stats={"episodes":count,"flour_success":0,"other_job_completions":0,
           "invalid_requests":0,"steps":0,"timeouts":0,"personal_reward":0.,
           "colony_reward":0.,"alternate_hauls":0}
    for i in range(count):
        world=Colony(seed+i,scenario)
        for _ in range(world.horizon):
            obs=world.vector()
            action=policy(obs)
            if not action_mask(obs)[action]:
                raise AssertionError("Evaluated policy selected masked task")
            _,_,done,info=world.step(action)
            stats["steps"]+=1
            stats["invalid_requests"]+=int(info["invalid"])
            stats["personal_reward"]+=info["personal_reward"]
            stats["colony_reward"]+=info["colony_reward"]
            stats["alternate_hauls"]+=int(
                info["flour_success"] and ACTIONS[action]=="HAUL_ALTERNATE")
            if done:
                stats["flour_success"]+=int(info["flour_success"])
                stats["other_job_completions"]+=int(info["other_job_success"])
                stats["timeouts"]+=int(info["timeout"])
                break
    stats["flour_rate"]=round(stats["flour_success"]/count,4)
    for label in ("personal_reward","colony_reward"):
        stats[label]=round(stats[label]/count,4)
    stats["mean_steps"]=round(stats["steps"]/count,4)
    return stats

def model_digest(model):
    payload={"schema":SCHEMA,"features":FEATURES,"actions":ACTIONS,
             "network":"15-24-6","origin":"SIMULATED_ONLY",
             "weights":{"w1":model.w1,"b1":model.b1,"w2":model.w2,"b2":model.b2},
             "minecraft_authorized":False}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,allow_nan=False).encode()).hexdigest()

def benchmark(train_seeds=(11,13,17),episodes=700,eval_count=90):
    scenarios=("standard","primary_empty","both_empty",
               "alternate_empty","no_secondary_job","supply_shift")
    rows=[]
    for seed in train_seeds:
        learned,training=train(seed,episodes)
        digest_before=model_digest(learned)
        untrained=QNetwork(seed+900)
        cases={}
        for index,scenario in enumerate(scenarios):
            start=700000000+index*1000000+seed*10000
            cases[scenario]={
                "heldout_seed_start":start,
                "neural_q":evaluate(lambda x:greedy(learned,x),start,scenario,eval_count),
                "scripted":evaluate(scripted,start,scenario,eval_count),
                "untrained":evaluate(lambda x:greedy(untrained,x),start,scenario,eval_count),
            }
        if model_digest(learned)!=digest_before:
            raise AssertionError("Evaluation changed frozen model")
        rows.append({"train_seed":seed,"model_sha256":digest_before,
                     "weights_frozen":True,"gradient_updates":training["updates"],
                     "scenarios":cases})
    return {"schema":"hearthbound.simulated-resource-task-switch.v1",
            "observation_schema":SCHEMA,"features":FEATURES,"actions":ACTIONS,
            "model_architecture":"15-24-6","training_origin":"SIMULATED_ONLY",
            "evaluation_origin":"SIMULATED_ONLY","minecraft_worlds":0,
            "minecraft_deployment_authorized":False,
            "neural_task_execution_authorized":False,
            "training_episodes_per_seed":episodes,"evaluation_episodes_per_cell":eval_count,
            "results":rows,
            "limitations":[
                "Synthetic resource supply, alternative occupation, and task durations",
                "No Minecraft navigation, Create machinery or reproduction",
                "Separate simulator-only schema v1; not the verified Minecraft v2 tensor",
                "No online reinforcement learning or deployment",
            ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--episodes",type=int,default=700)
    p.add_argument("--heldout",type=int,default=90)
    p.add_argument("--output",type=Path,default=Path("resource-switch-results.json"))
    a=p.parse_args()
    data=benchmark(episodes=a.episodes,eval_count=a.heldout)
    a.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    for row in data["results"]:
        for name,c in row["scenarios"].items():
            print("SIMULATED_RESOURCE_SWITCH seed="+str(row["train_seed"]),
                  "scenario="+name,
                  "neural="+str(c["neural_q"]["flour_rate"]),
                  "scripted="+str(c["scripted"]["flour_rate"]),
                  "untrained="+str(c["untrained"]["flour_rate"]),
                  "other_job_neural="+str(c["neural_q"]["other_job_completions"]))
    print("SIMULATED_RESOURCE_TASK_SWITCH_COMPLETE minecraft_worlds=0")
if __name__=="__main__":main()
