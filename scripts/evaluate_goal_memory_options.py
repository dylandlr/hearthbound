#!/usr/bin/env python3
"""v0.10.3: persistent option memory over frozen neural task Q-values.

SIMULATED_ONLY. No recurrent neural weights, LLMs, Forge, or Minecraft control.
This tests whether structured goal retention fixes task diversion; the memory
scheduler is intentionally a hand-authored baseline and is labelled as such.
"""
import argparse
import json
from pathlib import Path

import train_resource_task_switch as base
import ablate_resource_task_rewards as rewards

SCHEMA="hearthbound.simulated-goal-option-memory.v1"
OPTIONS=("SEEK_WHEAT","SECONDARY_ONCE","WAIT_RECHECK","DONE")
EVAL_SCENARIOS=rewards.EVAL_SCENARIOS
SEEDS=rewards.SEEDS

class GoalMemory:
    """Explicit per-episode memory; not privileged access to hidden supplies."""
    def __init__(self):
        self.primary_goal="PRODUCE_FLOUR"
        self.option="SEEK_WHEAT"
        self.secondary_completed=False
        self.returned_to_primary=False
        self.secondary_started=False
        self.option_transitions=[]
        self.last_event=None

    def transition(self,new,step):
        if new not in OPTIONS:
            raise ValueError("Unknown option")
        if self.option!=new:
            if self.option=="SECONDARY_ONCE" and new=="SEEK_WHEAT":
                self.returned_to_primary=True
            self.option_transitions.append({"step":step,"from":self.option,"to":new})
        self.option=new

    def observe(self,event,step):
        self.last_event=event
        if event=="OTHER_TASK_COMPLETE":
            self.secondary_completed=True
            self.transition("SEEK_WHEAT",step)
        elif event=="FLOUR_TASK_COMPLETE":
            self.transition("DONE",step)

def choose(memory,observation,model,step):
    if memory.option=="DONE":
        raise ValueError("Terminal goal cannot choose action")
    mask=base.action_mask(observation)
    if not any(mask):
        raise AssertionError("No legal option action")

    # Task options use *observed*, bounded resource knowledge only.
    # Prefer known available sources; let the trained Q-model break ties.
    available=[a for a in (2,3) if mask[a]]
    if available:
        memory.transition("SEEK_WHEAT",step)
        q=model.values(observation)[2]
        return max(available,key=lambda a:q[a])

    inspect=[a for a in (0,1) if (a==0 and observation[5] or
                                  a==1 and observation[10])]
    if inspect:
        memory.transition("SEEK_WHEAT",step)
        q=model.values(observation)[2]
        return max(inspect,key=lambda a:q[a])

    if mask[4] and not memory.secondary_completed and not memory.secondary_started:
        memory.transition("SECONDARY_ONCE",step)
        memory.secondary_started=True
        return 4

    memory.transition("WAIT_RECHECK",step)
    return 5

def rollout(model,seed,scenario,policy,trace=False):
    world=base.Colony(seed,scenario)
    memory=GoalMemory()
    results={"seed":seed,"flour":False,"other_job":False,"steps":0,
             "invalid":0,"colony_reward":0.,"personal_reward":0.,
             "secondary_then_resumed":False,"alternate_haul":False,
             "events":[],"option_transitions":[]}
    for _ in range(world.horizon):
        obs=world.vector()
        if policy=="neural_goal_bonus":
            act=base.greedy(model,obs)
        elif policy=="hierarchical_memory":
            act=choose(memory,obs,model,world.steps)
        elif policy=="scripted":
            act=base.scripted(obs)
        else:
            raise ValueError("Unknown comparator")
        if not base.action_mask(obs)[act]:
            raise AssertionError("Masked game action selected")
        _,_,done,info=world.step(act)
        if policy=="hierarchical_memory":
            memory.observe(info["event"],world.steps)
        results["colony_reward"]+=info["colony_reward"]
        results["personal_reward"]+=info["personal_reward"]
        results["alternate_haul"]|=info["event"]=="FLOUR_TASK_COMPLETE" and act==3
        if trace:
            results["events"].append({
                "step":world.steps,"action":base.ACTIONS[act],
                "event":info["event"],"primary_goal":"PRODUCE_FLOUR",
                "option":memory.option if policy=="hierarchical_memory" else "NONE",
                "source_flags":list(obs[5:8])+list(obs[10:13]),
            })
        if done:break
    results["flour"]=world.flour_done
    results["other_job"]=world.other_done
    results["steps"]=world.steps
    results["invalid"]=world.invalid_count
    results["colony_reward"]=round(results["colony_reward"],5)
    results["personal_reward"]=round(results["personal_reward"],5)
    results["secondary_then_resumed"]=memory.returned_to_primary
    results["option_transitions"]=memory.option_transitions if trace else []
    return results

def aggregate(rows):
    episodes=len(rows)
    return {
        "episodes":episodes,
        "flour_success":sum(r["flour"] for r in rows),
        "flour_rate":round(sum(r["flour"] for r in rows)/episodes,5),
        "secondary_job_completion":sum(r["other_job"] for r in rows),
        "resumed_primary_after_secondary":sum(r["secondary_then_resumed"] for r in rows),
        "alternate_flour_hauls":sum(r["alternate_haul"] for r in rows),
        "invalid_requests":sum(r["invalid"] for r in rows),
        "mean_steps":round(sum(r["steps"] for r in rows)/episodes,5),
        "colony_reward_per_episode":round(sum(r["colony_reward"] for r in rows)/episodes,5),
        "personal_reward_per_episode":round(sum(r["personal_reward"] for r in rows)/episodes,5),
    }

def benchmark(seeds=SEEDS,training_episodes=350,heldout=40):
    if len(set(seeds))!=len(seeds) or not seeds or training_episodes<1 or heldout<1:
        raise ValueError("Invalid seeds or episode budget")
    results=[]
    for seed in seeds:
        # Reproduce existing goal-bonus reward policy exactly; do not retrain a new
        # policy specifically for the hierarchy or use evaluation outcome labels.
        model,_=rewards.train("goal_bonus",seed,training_episodes)
        digest=base.model_digest(model)
        cases={}
        for i,scenario in enumerate(EVAL_SCENARIOS):
            start=700000000+i*1000000+seed*10000
            entries={}
            for policy in ("neural_goal_bonus","hierarchical_memory","scripted"):
                episodes=[rollout(model,start+j,scenario,policy) for j in range(heldout)]
                entries[policy]=aggregate(episodes)
            # Traces are illustrative examples from held-out episodes, not model training.
            entries["trace"]=rollout(model,start,scenario,"hierarchical_memory",trace=True)
            entries["seed_start"]=start
            cases[scenario]=entries
        if base.model_digest(model)!=digest:
            raise AssertionError("Evaluation modified a frozen neural checkpoint")
        results.append({"training_seed":seed,"model_sha256":digest,
                        "frozen":True,"scenarios":cases})
    return {
        "schema":SCHEMA,"observation_schema":base.SCHEMA,
        "architecture":"15-24-6 frozen goal-bonus Q, handcrafted option scheduler",
        "primary_goal":"PRODUCE_FLOUR","options":OPTIONS,
        "training_origin":"SIMULATED_ONLY","evaluation_origin":"SIMULATED_ONLY",
        "minecraft_worlds":0,"minecraft_task_dispatch_authorized":False,
        "recurrent_network_trained":False,"new_neural_weights_trained":False,
        "training_episodes_per_seed":training_episodes,
        "heldout_episodes_per_scenario_seed":heldout,
        "results":results,
        "limitations":[
            "Memory scheduler is hand-designed, not an end-to-end learned hierarchy",
            "Only source flags and observed task events are read; no hidden source contents",
            "Identical initial seeds do not ensure identical RNG streams after divergent actions",
            "Minecraft pathfinding, job contention, social decisions and persistent saving are absent",
        ],
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--training-episodes",type=int,default=350)
    parser.add_argument("--heldout",type=int,default=40)
    parser.add_argument("--output",type=Path,default=Path("hierarchical-goal-memory.json"))
    args=parser.parse_args()
    data=benchmark(training_episodes=args.training_episodes,heldout=args.heldout)
    args.output.write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
    for row in data["results"]:
        for scenario,case in row["scenarios"].items():
            print("GOAL_MEMORY_SIM seed="+str(row["training_seed"]), "scenario="+scenario,
                  "neural="+str(case["neural_goal_bonus"]["flour_rate"]),
                  "memory="+str(case["hierarchical_memory"]["flour_rate"]),
                  "scripted="+str(case["scripted"]["flour_rate"]),
                  "resumptions="+str(case["hierarchical_memory"]["resumed_primary_after_secondary"]))
    print("GOAL_MEMORY_COMPLETE simulator_only=true minecraft_worlds=0")
if __name__=="__main__":
    main()
