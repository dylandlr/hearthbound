#!/usr/bin/env python3
"""Outer holdout: imperfect sensor refreshes, resource drift, and refresh budgets.

Every result is SIMULATED_ONLY. Both policy arms experience the same
scenario/profile/seed fault schedule; current-state checks belong solely
to the independent task safety supervisor. Neural weights are frozen.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

import train_resource_task_switch as base
import ablate_resource_task_rewards as reward
import train_learned_option_controller as legacy
import train_age_aware_option_controller as age

SCHEMA="hearthbound.sensor-fault-outer-holdout.v1"
POLICIES=("age_aware","age_aware_budgeted","frozen_legacy")
# Explicitly outside the training delay set {0,2,3,4} and training interruptions.
FAULTS={
    "refresh_failures":{"horizon":35,"delay":5,"interrupt_every":0,
                        "fail_mod":2,"budget":4,"drift_every":0},
    "limited_refresh":{"horizon":35,"delay":6,"interrupt_every":0,
                       "fail_mod":0,"budget":2,"drift_every":0},
    "inventory_drift":{"horizon":35,"delay":5,"interrupt_every":0,
                       "fail_mod":0,"budget":4,"drift_every":5},
    "combined_faults":{"horizon":49,"delay":7,"interrupt_every":6,
                       "fail_mod":2,"budget":3,"drift_every":7},
}
SCENARIOS=("standard","primary_empty","both_empty","alternate_empty","supply_shift")
SEEDS=(11,13,17)

def fault_at(seed,step,tag,mod):
    """Fault outcomes keyed to absolute episode seed/step, not action RNG."""
    if not mod:return False
    material=f"{seed}|{step}|{tag}".encode()
    return int.from_bytes(hashlib.sha256(material).digest()[:4],"big")%mod==0

class FaultWorld(age.DelayedWorld):
    def __init__(self,seed,scenario,profile):
        super().__init__(seed,scenario,profile)
        self.seed=seed
        self.profile=profile
        self.refresh_attempts=0
        self.refresh_failures=0
        self.refresh_budget_denials=0
        self.inventory_drift_events=0
        self.age_observed=[]
    def sense(self):
        observation,elapsed=super().sense()
        self.age_observed.append(elapsed)
        return observation,elapsed
    def act_faulted(self,choice,low,observation,elapsed,allow_refresh,trace=False):
        step=self.world.steps+1
        refresh_attempt=(choice==3 and
                         not (self.interrupt_every and step%self.interrupt_every==0))
        if refresh_attempt:
            self.refresh_attempts+=1
            if not allow_refresh:
                self.refresh_budget_denials+=1
                choice=2  # WAIT, no free sensor capture
        rejected_before=self.rejections
        # Execution-time preflight has authority to read current inventory,
        # unlike the neural policy. The observation mask alone cannot know
        # that hidden stock changed since the last sensor update.
        proposed=None
        interrupted=(self.interrupt_every and step%self.interrupt_every==0)
        if not interrupted:
            if choice==0:
                proposed=legacy.execute(0,observation,low)
            elif choice==1:
                proposed=4
        stale_hazard=(proposed==2 and self.world.supply["primary"]<1 or
                      proposed==3 and self.world.supply["alternate"]<1 or
                      proposed==4 and (not self.world.other_available or
                                       self.world.other_done))
        if stale_hazard:
            self.rejections+=1
            # Trusted gate substitutes WAIT, but does not rewrite the policy's
            # remembered intent or magically correct stale observation flags.
            choice=2
        _,done,info=super().act(choice,low,observation,elapsed,record=False)
        actual_refresh=(choice==3 and not
                        (self.interrupt_every and step%self.interrupt_every==0))
        if actual_refresh and fault_at(self.seed,step,"refresh",self.profile["fail_mod"]):
            self.refresh_failures+=1
            self.forced_current=None
        # Changes after action commit; hidden from the prior decision. The
        # same tick/seed drift pattern is used for all policy families.
        if self.profile["drift_every"] and step%self.profile["drift_every"]==0:
            new_stock=1 if fault_at(self.seed,step,"restock",2) else 0
            self.world.supply["primary"]=new_stock
            self.inventory_drift_events+=1
            # No mutation to an already emitted sensor sample.
        if trace:
            self.events.append({
                "step":step,"chosen_option":age.OPTIONS[choice],
                "observed_age":elapsed,"result":info["event"],
                "supervisor_rejected":self.rejections>rejected_before,
                "refresh_failed":actual_refresh and self.forced_current is None,
                "primary_drift":bool(self.profile["drift_every"] and
                                      step%self.profile["drift_every"]==0),
                "actual_inventory_redacted":True,
            })
        return done,info

def replay(new,old,low,seed,scenario,profile,policy,trace=False):
    if policy not in POLICIES:raise ValueError("Unknown policy")
    w=FaultWorld(seed,scenario,profile)
    memory=legacy.AgentHistory()
    for _ in range(w.world.horizon):
        obs,elapsed=w.sense()
        if policy=="frozen_legacy":
            option=legacy.best(old,memory.state(obs),legacy.mask(obs))
            # This comparator has the original three options; remap by index.
            chosen=option
        else:
            chosen=age.select(new,w.memory.encode(obs,elapsed),age.option_mask(obs))
        # Budgeted variant is explicitly an engineered execution constraint;
        # it does not retrain the neural policy and denied refresh => WAIT.
        allow=(policy!="age_aware_budgeted" or
               w.refreshes < profile["budget"])
        before=w.rejections
        done,info=w.act_faulted(chosen,low,obs,elapsed,allow,trace)
        if policy=="frozen_legacy" and not (w.interrupt_every and
                                           w.world.steps%w.interrupt_every==0):
            memory.register(option,info["event"])
        if done:break
    return {
        "seed":seed,"flour_success":w.world.flour_done,
        "secondary_completed":w.world.other_done,
        "steps":w.world.steps,
        "supervisor_rejections":w.rejections,
        "executed_invalid_requests":w.world.invalid_count,
        "refresh_attempts":w.refresh_attempts,
        "refresh_executed":w.refreshes,
        "refresh_failures":w.refresh_failures,
        "refresh_budget_denials":w.refresh_budget_denials,
        "inventory_drift_events":w.inventory_drift_events,
        "max_observed_age":max(w.age_observed),
        "colony_reward":round(w.colony,6),
        "personal_reward":round(w.personal,6),
        "interruption_count":w.interruptions,
        "trace":w.events if trace else [],
    }

def summarize(results):
    count=len(results)
    decisions=sum(r["steps"]-r["interruption_count"] for r in results)
    rejected=sum(r["supervisor_rejections"] for r in results)
    return {
        "episodes":count,
        "flour_success":sum(r["flour_success"] for r in results),
        "success_rate":round(sum(r["flour_success"] for r in results)/count,6),
        "supervisor_rejections":rejected,
        "unintervened_valid_proposal_rate":round(1-rejected/max(1,decisions),6),
        "executed_invalid_requests":sum(r["executed_invalid_requests"] for r in results),
        "refresh_attempts":sum(r["refresh_attempts"] for r in results),
        "refresh_executed":sum(r["refresh_executed"] for r in results),
        "refresh_failures":sum(r["refresh_failures"] for r in results),
        "budget_denials":sum(r["refresh_budget_denials"] for r in results),
        "inventory_drift_events":sum(r["inventory_drift_events"] for r in results),
        "mean_steps":round(sum(r["steps"] for r in results)/count,6),
        "colony_reward_per_episode":round(sum(r["colony_reward"] for r in results)/count,6),
        "personal_reward_per_episode":round(sum(r["personal_reward"] for r in results)/count,6),
    }

def benchmark(seeds=SEEDS,low_episodes=350,old_episodes=480,
              age_episodes=520,heldout=24):
    if not seeds or len(set(seeds))!=len(seeds) or min(
            low_episodes,old_episodes,age_episodes,heldout)<1:
        raise ValueError("Invalid experiment budget")
    entries=[]
    for seed in seeds:
        low,_=reward.train("goal_bonus",seed,low_episodes)
        old,_=legacy.train_meta(seed,low,old_episodes)
        new,_=age.train(seed,low,age_episodes)
        originals=(base.model_digest(low),legacy.digest(old),age.digest(new))
        profiles={}
        for p_index,(profile_name,profile) in enumerate(FAULTS.items()):
            cases={}
            for s_index,scenario in enumerate(SCENARIOS):
                start=1230000000+seed*100000+p_index*10000+s_index*1000
                comparison={}
                for policy in POLICIES:
                    results=[replay(new,old,low,start+i,scenario,profile,policy)
                             for i in range(heldout)]
                    comparison[policy]=summarize(results)
                comparison["seed_start"]=start
                comparison["trace"]=replay(new,old,low,start,scenario,profile,
                                            "age_aware_budgeted",True)["trace"]
                cases[scenario]=comparison
            profiles[profile_name]=cases
        if originals!=(base.model_digest(low),legacy.digest(old),age.digest(new)):
            raise AssertionError("Frozen model mutated during outer holdout")
        entries.append({
            "train_seed":seed,"model_digests":originals,
            "frozen_checkpoints":True,"profiles":profiles,
        })
    return {
        "schema":SCHEMA,"model_training_origin":"SIMULATED_ONLY",
        "evaluation_origin":"SIMULATED_ONLY",
        "outer_profiles_unseen_in_training":True,
        "minecraft_worlds":0,"minecraft_task_authorized":False,
        "policy_arms":POLICIES,"fault_profiles":FAULTS,"scenarios":SCENARIOS,
        "episodes_per_cell":heldout,"results":entries,
        "notes":[
            "All fault profiles are held out from training; environmental laws remain abstract",
            "Budgeted policy applies an engineered refresh cap, no new training",
            "Safety supervisor inspects current validity and replaces unsafe tasks with WAIT",
            "Observed age is explicit; post-tick refresh failures retain delayed sensor queue",
            "Agent action selection never receives true inventory quantities",
        ],
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--low-episodes",type=int,default=350)
    p.add_argument("--old-episodes",type=int,default=480)
    p.add_argument("--age-episodes",type=int,default=520)
    p.add_argument("--heldout",type=int,default=24)
    p.add_argument("--output",type=Path,default=Path("sensor-fault-outer-holdout.json"))
    a=p.parse_args()
    report=benchmark(low_episodes=a.low_episodes,old_episodes=a.old_episodes,
                     age_episodes=a.age_episodes,heldout=a.heldout)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    for name in FAULTS:
        scenes=[row["profiles"][name][scenario] for row in report["results"]
                for scenario in SCENARIOS]
        print("SENSOR_FAULT_OUTER",name,
              " ".join(policy+"_success="+str(round(
                  sum(s[policy]["success_rate"] for s in scenes)/len(scenes),4))
                  for policy in POLICIES),
              " ".join(policy+"_rejects="+str(sum(
                  s[policy]["supervisor_rejections"] for s in scenes))
                  for policy in POLICIES),
              " ".join(policy+"_refresh="+str(sum(
                  s[policy]["refresh_executed"] for s in scenes))
                  for policy in POLICIES))
    print("SENSOR_FAULT_OUTER_COMPLETE minecraft_worlds=0")
if __name__=="__main__":main()
