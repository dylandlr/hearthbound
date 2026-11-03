#!/usr/bin/env python3
"""Hearthbound v0.10.8: learn value-of-information without a hard refresh quota.

Separate 21->24->4 neural Q policy, same age-aware observations and bounded
option executor. Train with synthetic refresh failures, occasional stock drift
and a *soft* refresh step cost. No Minecraft execution, no privileged sensors.
"""
import argparse
import copy
import json
import random
from pathlib import Path

import train_resource_task_switch as base
import ablate_resource_task_rewards as rewards
import train_learned_option_controller as legacy
import train_age_aware_option_controller as age
import evaluate_sensor_fault_outer_holdout as outer

SCHEMA="hearthbound.adaptive-sensing-cost.v1"
COSTS={"free":0., "low":.04, "medium":.12}
# Only parameterizations in train, separate from outer test delay {5,6,7}.
TRAIN_PROFILES=(
    {"horizon":28,"delay":0,"interrupt_every":0,"fail_mod":0,"drift_every":0},
    {"horizon":28,"delay":2,"interrupt_every":0,"fail_mod":3,"drift_every":0},
    {"horizon":28,"delay":4,"interrupt_every":4,"fail_mod":3,"drift_every":6},
    {"horizon":35,"delay":3,"interrupt_every":5,"fail_mod":2,"drift_every":9},
)

def train(seed,low,episodes,cost):
    if episodes<1 or cost not in COSTS.values():
        raise ValueError("Unregistered observation cost or episode count")
    rng=random.Random(seed+650000)
    online=age.Network(seed+650000)
    target=copy.deepcopy(online)
    replay=[]
    updates=0
    for ep in range(episodes):
        profile=TRAIN_PROFILES[ep%len(TRAIN_PROFILES)]
        scenario=rewards.TRAIN_SCENARIOS[(ep//len(TRAIN_PROFILES))%len(rewards.TRAIN_SCENARIOS)]
        env=outer.FaultWorld(55000000+seed*100000+ep,scenario,profile)
        epsilon=.08+.8*max(0.,1.-ep/(episodes*.85))
        for _ in range(env.world.horizon):
            obs,elapsed=env.sense()
            x=env.memory.encode(obs,elapsed)
            legal=age.option_mask(obs)
            valid=[i for i,allowed in enumerate(legal) if allowed]
            action=rng.choice(valid) if rng.random()<epsilon else age.select(online,x,legal)
            rejected_before=env.rejections
            refresh_before=env.refreshes
            done,info=env.act_faulted(action,low,obs,elapsed,allow_refresh=True)
            attempted_refresh=int(env.refreshes>refresh_before)
            # Reward is *only* used for TD training; environment reports are unchanged.
            td_reward=info["personal_reward"]+info["colony_reward"]
            td_reward-=cost*attempted_refresh
            td_reward-=.18*int(env.rejections>rejected_before)
            after_obs,after_age=env.sense()
            nx=env.memory.encode(after_obs,after_age)
            replay.append((x,action,td_reward,nx,done,age.option_mask(after_obs)))
            if len(replay)>6000:replay.pop(0)
            if len(replay)>=48:
                for prior,a,r,following,terminal,valid_next in rng.sample(replay,8):
                    future=0. if terminal else max(
                        q for q,allowed in zip(target.values(following)[2],valid_next) if allowed)
                    online.update(prior,a,r+age.GAMMA*future)
                    updates+=1
                if updates%1600==0:target=copy.deepcopy(online)
            if done:break
    return online,updates

def compare(seeds=(11,13,17),low_episodes=350,train_episodes=480,
            legacy_episodes=520,heldout=16):
    rows=[]
    for seed in seeds:
        low,_=rewards.train("goal_bonus",seed,low_episodes)
        existing,_=age.train(seed,low,legacy_episodes)
        variants={key:train(seed,low,train_episodes,cost) for key,cost in COSTS.items()}
        hashes={key:age.digest(net) for key,(net,_) in variants.items()}
        hashes["legacy"]=age.digest(existing)
        results={}
        for pi,(profile_name,profile) in enumerate(outer.FAULTS.items()):
            scenarios={}
            for si,scenario in enumerate(outer.SCENARIOS):
                start=1340000000+seed*100000+pi*10000+si*1000
                cases={}
                for name,network in [(key,v[0]) for key,v in variants.items()]+[("legacy",existing)]:
                    receipts=[outer.replay(network,None,low,start+i,scenario,profile,
                                           "age_aware",False)
                              for i in range(heldout)]
                    cases[name]=outer.summarize(receipts)
                cases["seed_start"]=start
                scenarios[scenario]=cases
            results[profile_name]=scenarios
        if any(age.digest(model)!=hashes[key] for key,(model,_) in variants.items()):
            raise AssertionError("Evaluation mutated trained network")
        if age.digest(existing)!=hashes["legacy"]:
            raise AssertionError("Legacy policy mutated")
        rows.append({"seed":seed,
                     "model_hashes":hashes,
                     "train_updates":{key:val[1] for key,val in variants.items()},
                     "results":results})
    return {"schema":SCHEMA,"training_origin":"SIMULATED_ONLY",
            "evaluation_origin":"SIMULATED_ONLY",
            "minecraft_worlds":0,"minecraft_task_authorized":False,
            "hard_refresh_budget":False,
            "soft_cost_per_refresh":COSTS,
            "training_fault_profiles":TRAIN_PROFILES,
            "outer_fault_profiles":outer.FAULTS,
            "heldout_episodes_per_cell":heldout,
            "results":rows,
            "notes":[
                "A soft TD penalty rewards efficient sensing; no artificial hard quota is enforced",
                "Local perception and task facts are automatically available through the original observation",
                "The Minecraft server runtime has not been benchmarked for actual sensor overhead",
                "Executor still requires independent current-world preflight before physical tasks",
                "Refresh and fault behavior are simulated; no neural Minecraft task execution",
            ]}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--low-episodes",type=int,default=350)
    p.add_argument("--train-episodes",type=int,default=480)
    p.add_argument("--legacy-episodes",type=int,default=520)
    p.add_argument("--heldout",type=int,default=16)
    p.add_argument("--output",type=Path,default=Path("adaptive-sensing-cost.json"))
    a=p.parse_args()
    r=compare(low_episodes=a.low_episodes,train_episodes=a.train_episodes,
              legacy_episodes=a.legacy_episodes,heldout=a.heldout)
    a.output.write_text(json.dumps(r,sort_keys=True,indent=2)+"\n")
    for profile in outer.FAULTS:
        cells=[row["results"][profile][scene] for row in r["results"] for scene in outer.SCENARIOS]
        message=[]
        for policy in (*COSTS,"legacy"):
            message.append(policy+"_success="+str(round(sum(c[policy]["success_rate"] for c in cells)/len(cells),4)))
            message.append(policy+"_refresh="+str(sum(c[policy]["refresh_executed"] for c in cells)))
            message.append(policy+"_rejected="+str(sum(c[policy]["supervisor_rejections"] for c in cells)))
        print("ADAPTIVE_SENSING",profile,*message)
    print("ADAPTIVE_SENSING_COMPLETE minecraft_worlds=0")
if __name__=="__main__":main()
