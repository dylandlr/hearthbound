#!/usr/bin/env python3
"""Frozen-policy, multi-seed stress benchmark; SIMULATED ONLY.

Use separately trained neural-Q models as immutable candidates, then stress
them on held-out environment seeds and explicit out-of-distribution states.
No Minecraft observations or online RL outcomes are manufactured here.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

from train_simulated_mill_neural_q import (
    ACTIONS, SCHEMA, NeuralQ, best, checkpoint, canonical, scripted, train
)

TRAINING_SEEDS=(11,13,17)
EVALUATION_SEED_BASE=400000000
SCENARIOS={
    "nominal": {"restock":0.30,"horizon":16,"initial_supply_probability":0.45},
    "scarce": {"restock":0.05,"horizon":16,"initial_supply_probability":0.15},
    "no_restock": {"restock":0.0,"horizon":16,"initial_supply_probability":0.15},
    "abundant": {"restock":0.80,"horizon":16,"initial_supply_probability":0.80},
    "short_horizon": {"restock":0.30,"horizon":5,"initial_supply_probability":0.45},
}
OOD_MACHINE_STATES={
    "unpowered":(0.,0.,0.,0.,0.,1.,0.,0.,0.,0.),
    "output_ready":(1.,0.,1.,0.,0.,1.,0.,0.,0.,0.),
    "blocked":(1.,0.,0.,1.,0.,1.,0.,0.,0.,0.),
    "busy":(1.,0.,0.,0.,0.,0.,0.,1.,1.,0.),
    "processing":(1.,1.,0.,0.,0.,0.,0.,1.,1.,0.),
    "stale_source":(1.,0.,0.,0.,0.,1.,0.,0.,0.,1.),
}

class StressWorld:
    def __init__(self,seed,config):
        self.rng=random.Random(seed)
        self.config=config
        self.supply=self.rng.random()<config["initial_supply_probability"]
        self.known="UNKNOWN"
        self.age=0
        self.steps=0
        self.finished=False

    def state(self):
        effective=self.known if self.age<=100 else "UNKNOWN"
        return (1.,0.,0.,0.,0.,float(effective=="UNKNOWN"),
                float(effective=="EMPTY"),float(effective=="AVAILABLE"),
                0.,float(self.age>100 and self.known!="UNKNOWN"))

    def step(self,idx):
        if self.finished or not 0<=idx<len(ACTIONS):
            raise ValueError("Invalid decision after completed episode")
        action=ACTIONS[idx]
        self.steps+=1
        colony=-0.02
        personal=0.
        invalid=False
        if action=="INSPECT_SOURCE":
            self.known="AVAILABLE" if self.supply else "EMPTY"
            self.age=0
        elif action=="WAIT_FOR_SUPPLY":
            if not self.supply and self.rng.random()<self.config["restock"]:
                self.supply=True
                self.known="UNKNOWN"
            self.age+=40
        else:
            if self.supply and self.known=="AVAILABLE" and self.age<=100:
                colony+=1.
                personal=1.
                self.supply=False
            else:
                colony-=0.15
                invalid=True
            self.age+=40
        timeout=self.steps>=self.config["horizon"] and personal!=1.
        self.finished=timeout or personal==1.
        return {
            "done":self.finished,"success":personal==1.,
            "timeout":timeout,"invalid":invalid,
            "colony":round(colony,6),"personal":personal,
        }

def neural_action(model,state):
    return best(model.values(state)[2])

def guarded_action(state,idx):
    """Python evaluation mirror of Java's fail-closed NeuralQContextGate."""
    if len(state)!=10 or not all(0<=v<=1 for v in state):
        raise ValueError("Invalid observation")
    if sum(state[5:8])!=1.:
        raise ValueError("Invalid source flags")
    if state[9] and state[5]!=1.:
        raise ValueError("Stale source knowledge is not unknown")
    if state[0]!=1. or state[1]!=0. or state[2]!=0. or state[3]!=0. or state[8]!=0.:
        return False
    if state[9]==1.:
        return False
    return state[5+idx]==1.

def evaluate(policy,seed,config,episodes):
    stats={
        "episodes":episodes,"successes":0,"timeouts":0,
        "invalid_requests":0,"steps":0,
        "colony_reward_total":0.,"personal_reward_total":0.,
        "guard_rejections":0,
    }
    for episode in range(episodes):
        world=StressWorld(seed+episode,config)
        for _ in range(config["horizon"]):
            observation=world.state()
            action_idx=policy(observation)
            # In-distribution simulation: action selection can be unsafe,
            # but invalid request penalties are always recorded.
            if not guarded_action(observation,action_idx):
                stats["guard_rejections"]+=1
                # Existing simulator baseline still tests actual proposed
                # choice. Guard results are only observational here.
            transition=world.step(action_idx)
            stats["steps"]+=1
            stats["colony_reward_total"]+=transition["colony"]
            stats["personal_reward_total"]+=transition["personal"]
            stats["invalid_requests"]+=int(transition["invalid"])
            if transition["done"]:
                stats["successes"]+=int(transition["success"])
                stats["timeouts"]+=int(transition["timeout"])
                break
    stats["success_rate"]=round(stats["successes"]/episodes,6)
    stats["mean_steps"]=round(stats["steps"]/episodes,6)
    stats["colony_reward_per_episode"]=round(stats.pop("colony_reward_total")/episodes,6)
    stats["personal_reward_per_episode"]=round(stats.pop("personal_reward_total")/episodes,6)
    return stats

def evaluate_ood(model):
    states={}
    for name,x in OOD_MACHINE_STATES.items():
        choice=neural_action(model,x)
        allowed=guarded_action(x,choice)
        states[name]={
            "raw_proposal":ACTIONS[choice],
            "gate":"ALLOW" if allowed else "ABSTAIN",
            "task_dispatched":False,
            "training_distribution":"OUT_OF_DISTRIBUTION",
        }
    return states

def benchmark(training_seeds=TRAINING_SEEDS,train_episodes=300,eval_episodes=80):
    if not training_seeds or len(set(training_seeds))!=len(training_seeds):
        raise ValueError("Require unique training seeds")
    if train_episodes<1 or eval_episodes<1:
        raise ValueError("Positive train/evaluation counts required")
    results=[]
    for training_seed in training_seeds:
        model,updates=train(training_seed,train_episodes)
        frozen=checkpoint(model,training_seed,train_episodes)
        fingerprint_before=hashlib.sha256(canonical(frozen).encode()).hexdigest()
        scenarios={}
        for scenario_index,(name,config) in enumerate(SCENARIOS.items()):
            # Evaluation randomness is disjoint from all simulator training
            # seeds, identical across policies, and independent by scenario.
            eval_seed=EVALUATION_SEED_BASE+scenario_index*1000000+training_seed*10000
            scenarios[name]={
                "environment":dict(config),
                "eval_seed_start":eval_seed,
                "neural_q":evaluate(lambda x:neural_action(model,x),eval_seed,config,eval_episodes),
                "scripted_reference":evaluate(scripted,eval_seed,config,eval_episodes),
                "untrained_network":evaluate(
                    lambda x:neural_action(NeuralQ(training_seed+900),x),
                    eval_seed,config,eval_episodes),
            }
        out_of_distribution=evaluate_ood(model)
        fingerprint_after=hashlib.sha256(canonical(checkpoint(model,training_seed,train_episodes)).encode()).hexdigest()
        if fingerprint_before!=fingerprint_after:
            raise AssertionError("Frozen evaluation unexpectedly changed model weights")
        results.append({
            "train_seed":training_seed,"gradient_updates":updates,
            "checkpoint_sha256":frozen["sha256"],"checkpoint_unchanged":True,
            "scenarios":scenarios,"ood_machine_states":out_of_distribution,
        })
    return {
        "schema":"hearthbound.simulated-neural-q-stress.v1",
        "observation_schema":SCHEMA,"training_data_origin":"SIMULATED_ONLY",
        "evaluation_data_origin":"SIMULATED_ONLY",
        "actual_minecraft_worlds":0,
        "neural_task_execution_authorized":False,
        "minecraft_learning_demonstrated":False,
        "train_episodes_per_model":train_episodes,
        "eval_episodes_per_scenario_per_model":eval_episodes,
        "independent_train_seeds":list(training_seeds),
        "scenario_count":len(SCENARIOS),
        "out_of_distribution_machine_conditions":list(OOD_MACHINE_STATES),
        "results":results,
        "limitations":[
            "simulator transition probabilities are assumed, not Minecraft-calibrated",
            "three seed variations are exploratory, not statistically conclusive",
            "frozen 3-action policy has no unpowered or output-handling actions",
            "guard statistics do not represent actual Minecraft interventions",
        ]
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--train-episodes",type=int,default=300)
    p.add_argument("--eval-episodes",type=int,default=80)
    p.add_argument("--output",type=Path,default=Path("simulated-neural-q-stress.json"))
    args=p.parse_args()
    result=benchmark(train_episodes=args.train_episodes,eval_episodes=args.eval_episodes)
    args.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    for row in result["results"]:
        print("SIMULATED_STRESS_MODEL",row["train_seed"],"checkpoint",row["checkpoint_sha256"])
        for name,values in row["scenarios"].items():
            print("SIMULATED_STRESS_SCENARIO seed="+str(row["train_seed"]),
                  "scenario="+name,
                  "neural="+str(values["neural_q"]["success_rate"]),
                  "scripted="+str(values["scripted_reference"]["success_rate"]),
                  "untrained="+str(values["untrained_network"]["success_rate"]))
    print("SIMULATED_NEURAL_Q_STRESS_COMPLETE models="+str(len(result["results"])),
          "minecraft_worlds=0")
if __name__=="__main__":
    main()
