#!/usr/bin/env python3
"""Frozen learned-option policy under unseen delay/interruption regimes.

All environments are synthetic. Agents receive only delayed observations;
an independent safety supervisor checks current state and rejects unsafe jobs.
This is never a live Minecraft action or model-weight update.
"""
import argparse
import json
import random
from collections import deque
from pathlib import Path

import train_resource_task_switch as base
import ablate_resource_task_rewards as rewards
import evaluate_goal_memory_options as engineered
import train_learned_option_controller as options

POLICIES=("learned_options","engineered_memory","frozen_neural","scripted")
SCENARIOS=("standard","primary_empty","both_empty","alternate_empty","supply_shift")
STRESS={
    "clean_long":{"horizon":28,"delay":0,"interrupt_every":0},
    "delayed_2":{"horizon":28,"delay":2,"interrupt_every":0},
    "delayed_4":{"horizon":28,"delay":4,"interrupt_every":0},
    "interrupt_4":{"horizon":28,"delay":0,"interrupt_every":4},
    "delayed_interrupt":{"horizon":42,"delay":3,"interrupt_every":5},
}
SEEDS=(11,13,17)

def replay(meta,low,seed,scenario,policy,profile,include_trace=False):
    if policy not in POLICIES: raise ValueError("Unknown comparator")
    if scenario not in SCENARIOS: raise ValueError("Unknown world regime")
    world=base.Colony(seed,scenario,horizon=profile["horizon"])
    history=options.AgentHistory()
    scripted_memory=engineered.GoalMemory()
    sensor_queue=deque()
    completion_queue=deque()
    safety_rejections=0
    forced_interruptions=0
    option_switches=0
    personal=colony=0.
    events=[]
    for _ in range(world.horizon):
        # The observation is pushed before the decision; delay=0 means
        # real current observation. Old observations are NOT silently
        # refreshed from the true state.
        sensor_queue.append(world.vector())
        sensed=sensor_queue[max(0,len(sensor_queue)-1-profile["delay"])]
        if profile["interrupt_every"] and (world.steps+1)%profile["interrupt_every"]==0:
            forced_interruptions+=1
            # External interruption consumes one world tick. Policies are
            # not allowed to execute their selected option in this tick.
            chosen=None
            primitive=5
            option_name="INTERRUPTED"
        elif policy=="learned_options":
            chosen=options.best(meta,history.state(sensed),options.mask(sensed))
            primitive=options.execute(chosen,sensed,low)
            option_name=options.OPTIONS[chosen]
        elif policy=="engineered_memory":
            chosen=None
            primitive=engineered.choose(scripted_memory,sensed,low,world.steps)
            option_name=scripted_memory.option
        elif policy=="frozen_neural":
            chosen=None
            primitive=base.greedy(low,sensed)
            option_name="NONE"
        else:
            chosen=None
            primitive=base.scripted(sensed)
            option_name="NONE"

        # Trusted safety supervisor must use the current valid world state
        # to reject stale proposals; it NEVER reveals those values to the
        # model or scripted policy before selection.
        permitted=base.action_mask(world.vector())
        if not permitted[primitive]:
            safety_rejections+=1
            primitive=5
            option_name+=":REJECTED"

        _,_,done,info=world.step(primitive)
        personal+=info["personal_reward"]
        colony+=info["colony_reward"]
        # Task completion notifications are delayed by the SAME transport
        # latency as observations, not delivered before they exist.
        completion_queue.append(info["event"])
        event=completion_queue[max(0,len(completion_queue)-1-profile["delay"])]
        if chosen is not None and primitive!=5:
            history.register(chosen,event)
        elif chosen is not None:
            # Even a rejected proposal should not mutate task memory into
            # a false "secondary job completed" event.
            history.register(chosen,"WAITED")
        if policy=="engineered_memory":
            scripted_memory.observe(event,world.steps)
        if include_trace:
            events.append({
                "step":world.steps,
                "perceived_option":option_name,
                "executed_action":base.ACTIONS[primitive],
                "received_event":event,
                "actual_event_after_step":info["event"],
                "rejected_by_safety_supervisor":option_name.endswith(":REJECTED"),
                "interruption":option_name=="INTERRUPTED",
            })
        if done:break
    return {
        "seed":seed,"flour_success":world.flour_done,
        "other_job":world.other_done,
        "steps":world.steps,
        "invalid_requests":world.invalid_count,
        "safety_rejections":safety_rejections,
        "forced_interruptions":forced_interruptions,
        "option_switches":history.switches,
        "returned_after_secondary":history.returned_to_primary,
        "personal_reward":round(personal,5),
        "colony_reward":round(colony,5),
        "trace":events,
    }

def aggregate(rows):
    n=len(rows)
    return {
        "episodes":n,
        "flour_success":sum(x["flour_success"] for x in rows),
        "flour_rate":round(sum(x["flour_success"] for x in rows)/n,6),
        "other_job_completions":sum(x["other_job"] for x in rows),
        "safety_rejections":sum(x["safety_rejections"] for x in rows),
        "invalid_requests":sum(x["invalid_requests"] for x in rows),
        "forced_interruptions":sum(x["forced_interruptions"] for x in rows),
        "option_switches":sum(x["option_switches"] for x in rows),
        "returned_after_secondary":sum(x["returned_after_secondary"] for x in rows),
        "mean_steps":round(sum(x["steps"] for x in rows)/n,6),
        "colony_reward":round(sum(x["colony_reward"] for x in rows)/n,6),
        "personal_reward":round(sum(x["personal_reward"] for x in rows)/n,6),
    }

def benchmark(seeds=SEEDS,low_episodes=350,meta_episodes=480,heldout=30):
    if not seeds or len(set(seeds))!=len(seeds) or min(low_episodes,meta_episodes,heldout)<1:
        raise ValueError("Invalid trial config")
    output=[]
    for train_seed in seeds:
        low,_=rewards.train("goal_bonus",train_seed,low_episodes)
        meta,_=options.train_meta(train_seed,low,meta_episodes)
        low_digest=base.model_digest(low)
        meta_digest=options.digest(meta)
        cases={}
        for profile_index,(profile_name,profile) in enumerate(STRESS.items()):
            cases[profile_name]={}
            for scenario_index,scenario in enumerate(SCENARIOS):
                # Entirely new test seed-space, no re-use of v0.10.4
                # held-out seeds or training seeds.
                start=950000000+train_seed*100000+profile_index*10000+scenario_index*1000
                measures={}
                for policy in POLICIES:
                    runs=[replay(meta,low,start+i,scenario,policy,profile)
                          for i in range(heldout)]
                    measures[policy]=aggregate(runs)
                measures["heldout_seed_start"]=start
                measures["learned_trace"]=replay(meta,low,start,scenario,
                                                 "learned_options",profile,True)["trace"]
                cases[profile_name][scenario]=measures
        if base.model_digest(low)!=low_digest or options.digest(meta)!=meta_digest:
            raise AssertionError("Frozen networks mutated during stress evaluation")
        output.append({
            "seed":train_seed,"low_model_sha256":low_digest,
            "meta_model_sha256":meta_digest,"frozen":True,"profiles":cases,
        })
    return {
        "schema":"hearthbound.option-interruption-stress.v1",
        "model_training_origin":"SIMULATED_ONLY",
        "evaluation_origin":"SIMULATED_ONLY",
        "minecraft_worlds_executed":0,
        "minecraft_action_authorized":False,
        "trained_memory":"LAST_OPTION_PLUS_LAST_OBSERVED_EVENT",
        "learned_option_selection":True,
        "option_executors":"HAND_DESIGNED",
        "policy_arms":list(POLICIES),
        "stress_profiles":STRESS,
        "scenarios":list(SCENARIOS),
        "heldout_episodes_per_cell":heldout,
        "training_seeds":list(seeds),
        "result":output,
        "notes":[
            "Delayed sensors and delayed event notifications are modeled with queues",
            "Supervisor sees current world masks only to reject unsafe proposed actions",
            "Shared seed guarantees matched initial world, not identical stochastic draws after different actions",
            "No policy trained on these unseen stress scenarios, no weight promotion",
            "Synthetic interruptions consume steps and do not represent actual Minecraft player behavior",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--low-episodes",type=int,default=350)
    p.add_argument("--meta-episodes",type=int,default=480)
    p.add_argument("--heldout",type=int,default=30)
    p.add_argument("--output",type=Path,default=Path("option-interruption-stress.json"))
    a=p.parse_args()
    result=benchmark(low_episodes=a.low_episodes,meta_episodes=a.meta_episodes,
                     heldout=a.heldout)
    a.output.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    for profile in STRESS:
        for name in SCENARIOS:
            result_rows=[row["profiles"][profile][name] for row in result["result"]]
            print("OPTION_STRESS",profile,name,
                  " ".join(k+"="+str(round(sum(row[k]["flour_rate"] for row in result_rows)
                                             /len(result_rows),4)) for k in POLICIES),
                  "safety_rejections="+str(sum(row["learned_options"]["safety_rejections"]
                                                for row in result_rows)))
    print("OPTION_STRESS_SIMULATION_COMPLETE minecraft_worlds=0")
if __name__=="__main__":main()
