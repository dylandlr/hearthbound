#!/usr/bin/env python3
"""Predeclared reward ablations for the 15-feature colony simulator.

Pure simulation. Preserve v0.10.1's original train() and model checkpoints.
Same random seeds and evaluation worlds; no LLMs or Minecraft control.
"""
import argparse
import copy
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import train_resource_task_switch as base

GAMMA=0.96
MODES=("original","goal_bonus","secondary_discount","potential_shaping")
TRAIN_SCENARIOS=("standard","primary_empty","both_empty","alternate_empty",
                 "no_secondary_job")
EVAL_SCENARIOS=TRAIN_SCENARIOS+("supply_shift",)
SEEDS=(11,13,17)

def potential(observation):
    # Knowledge potential is bounded, and terminal potential is zero.
    return 0.15*observation[7]+0.15*observation[12]

class AblationColony(base.Colony):
    def __init__(self,seed,scenario,mode):
        super().__init__(seed,scenario)
        if mode not in MODES:
            raise ValueError("Invalid registered reward mode")
        self.mode=mode

    def step(self,index):
        prior=self.vector()
        next_obs,old_reward,done,info=super().step(index)
        personal=info["personal_reward"]
        colony=info["colony_reward"]
        # Preserve the environment, action mask, and *reported* original reward.
        # Ablations modify only the TD training target.
        if self.mode=="original":
            reward=old_reward
        elif self.mode=="goal_bonus":
            reward=old_reward+(1.0 if info["flour_success"] else 0.0)
        elif self.mode=="secondary_discount":
            reward=old_reward-(0.5 if info["event"]=="OTHER_TASK_COMPLETE" else 0.0)
        else:
            reward=old_reward+GAMMA*(0.0 if done else potential(next_obs))-potential(prior)
        info={**info,"training_reward":round(reward,5),
              "unmodified_colony_reward":colony,
              "unmodified_personal_reward":personal}
        return next_obs,round(reward,5),done,info

def train(mode,seed,episodes):
    if mode not in MODES or episodes<1:
        raise ValueError("Unknown ablation or empty training budget")
    # Exact same network seed, exploration schedule and minibatch algorithm as v0.10.1.
    rng=random.Random(seed)
    network=base.QNetwork(seed)
    target=copy.deepcopy(network)
    replay=[]
    updates=0
    for ep in range(episodes):
        env=AblationColony(10000000+seed*100000+ep,
                           TRAIN_SCENARIOS[ep%len(TRAIN_SCENARIOS)],mode)
        epsilon=0.07+0.83*max(0.,1.-ep/(episodes*.8))
        for _ in range(env.horizon):
            obs=env.vector()
            candidates=[i for i,allowed in enumerate(base.action_mask(obs)) if allowed]
            action=rng.choice(candidates) if rng.random()<epsilon else base.greedy(network,obs)
            nxt,reward,done,_=env.step(action)
            replay.append((obs,action,reward,nxt,done))
            if len(replay)>6000:replay.pop(0)
            if len(replay)>=48:
                for x,a,r,nx,terminal in rng.sample(replay,12):
                    future=0. if terminal else max(q for q,ok in
                        zip(target.values(nx)[2],base.action_mask(nx)) if ok)
                    network.update(x,a,r+GAMMA*future)
                    updates+=1
                if updates%1200==0:
                    target=copy.deepcopy(network)
            if done:break
    return network,updates

def evaluate(model,scenario,start,episodes):
    result={"episodes":episodes,"flour_success":0,"other_job_completions":0,
            "other_job_before_flour":0,"invalid_requests":0,
            "alternate_hauls":0,"timeouts":0,"total_steps":0,
            "personal_reward_total":0.,"colony_reward_total":0.,
            "action_counts":{name:0 for name in base.ACTIONS},
            "per_episode":[]}
    for ep in range(episodes):
        # Evaluation always uses unmodified v0.10.1 world and reward contract!
        world=base.Colony(start+ep,scenario)
        completed_other_before_flour=False
        for _ in range(world.horizon):
            obs=world.vector()
            action=base.greedy(model,obs)
            if not base.action_mask(obs)[action]:
                raise AssertionError("Evaluation selected a masked action")
            _,_,done,info=world.step(action)
            result["action_counts"][base.ACTIONS[action]]+=1
            result["total_steps"]+=1
            result["invalid_requests"]+=int(info["invalid"])
            result["personal_reward_total"]+=info["personal_reward"]
            result["colony_reward_total"]+=info["colony_reward"]
            if info["event"]=="OTHER_TASK_COMPLETE":
                completed_other_before_flour=True
            if info["event"]=="FLOUR_TASK_COMPLETE" and action==3:
                result["alternate_hauls"]+=1
            if done:break
        result["flour_success"]+=int(world.flour_done)
        result["other_job_completions"]+=int(world.other_done)
        result["other_job_before_flour"]+=int(completed_other_before_flour)
        result["timeouts"]+=int(not world.flour_done)
        result["per_episode"].append({
            "episode_seed":start+ep,
            "flour_success":world.flour_done,
            "other_job_done":world.other_done,
            "steps":world.steps,
            "invalid_requests":world.invalid_count,
        })
    result["success_rate"]=round(result["flour_success"]/episodes,6)
    result["mean_steps"]=round(result["total_steps"]/episodes,6)
    result["colony_reward_per_episode"]=round(result.pop("colony_reward_total")/episodes,6)
    result["personal_reward_per_episode"]=round(result.pop("personal_reward_total")/episodes,6)
    result["other_job_rate"]=round(result["other_job_completions"]/episodes,6)
    return result

def benchmark(training_seeds=SEEDS,train_episodes=350,heldout=40):
    if len(training_seeds)!=len(set(training_seeds)) or not training_seeds:
        raise ValueError("Training seeds must be unique")
    if train_episodes<1 or heldout<1:
        raise ValueError("Positive episode counts required")
    rows=[]
    for seed in training_seeds:
        learned={}
        for mode in MODES:
            model,updates=train(mode,seed,train_episodes)
            digest=base.model_digest(model)
            learned[mode]={"model":model,"updates":updates,"sha256":digest}
        cases={}
        for scenario_idx,scenario in enumerate(EVAL_SCENARIOS):
            start=700000000+scenario_idx*1000000+seed*10000
            cases[scenario]={
                "heldout_seed_start":start,
                "scripted":base.evaluate(base.scripted,start,scenario,heldout),
            }
            for mode,entry in learned.items():
                cases[scenario][mode]=evaluate(entry["model"],scenario,start,heldout)
        for mode,entry in learned.items():
            if base.model_digest(entry["model"])!=entry["sha256"]:
                raise AssertionError("Evaluation altered model weights")
        rows.append({
            "train_seed":seed,
            "models":{mode:{"sha256":v["sha256"],"updates":v["updates"],
                            "frozen_after_training":True}
                      for mode,v in learned.items()},
            "scenarios":cases,
        })
    return {
        "schema":"hearthbound.simulated-task-reward-ablation.v1",
        "observation_schema":base.SCHEMA,
        "actions":list(base.ACTIONS),
        "modes":list(MODES),
        "training_seeds":list(training_seeds),
        "training_episodes_per_mode_seed":train_episodes,
        "heldout_episodes_per_scenario_seed":heldout,
        "evaluation_scenarios":list(EVAL_SCENARIOS),
        "training_reward_variants":{
            "original":"Unmodified v0.10.1 personal+colony reward",
            "goal_bonus":"Add +1.0 to TD reward for flour completion",
            "secondary_discount":"Subtract 0.5 from TD reward for other job completion",
            "potential_shaping":"Gamma*Phi(s')-Phi(s), terminal Phi=0, Phi=0.15 per known available source",
        },
        "evaluation_reward_contract":"UNMODIFIED_V0_10_1",
        "world_origin":"SIMULATED_ONLY",
        "minecraft_worlds":0,
        "minecraft_learning_claimed":False,
        "neural_execution_authorized":False,
        "results":rows,
        "caveats":[
            "Matched episode seeds give identical initial conditions, not necessarily identical exogenous draws after divergent actions",
            "Original mode is a fresh deterministic reproduction of v0.10.1; compare hashes and metrics before attributing changes",
            "Secondary task completion is logged separately from flour and neither substitutes for the other",
            "No sequential transfer to Minecraft or real-world reward effect is demonstrated",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--train-episodes",type=int,default=350)
    p.add_argument("--heldout",type=int,default=40)
    p.add_argument("--output",type=Path,default=Path("simulated-task-reward-ablation.json"))
    args=p.parse_args()
    data=benchmark(train_episodes=args.train_episodes,heldout=args.heldout)
    args.output.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    for row in data["results"]:
        for scenario,case in row["scenarios"].items():
            print("SIM_REWARD_ABLATION",row["train_seed"],scenario,
                  " ".join(f"{mode}={case[mode]['success_rate']:.4f}" for mode in MODES),
                  f"scripted={case['scripted']['flour_rate']:.4f}")
    print("SIM_REWARD_ABLATION_COMPLETE minecraft_worlds=0")
if __name__=="__main__":
    main()
