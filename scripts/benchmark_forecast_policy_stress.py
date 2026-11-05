#!/usr/bin/env python3
"""Precommitted out-of-distribution synthetic resource schedules.

Freeze one previously defined GRU per training seed, then replay SCRIPTED,
greedy and age-blend policies against exactly identical policy-independent
latent sequences. No retraining, tuning, hidden labels or Forge deployment.
"""
import argparse
import hashlib
import json
import random
import statistics
from pathlib import Path
import numpy as np

from benchmark_forecast_policy_gating import episode,ARMS
from benchmark_observed_change_forecast import train as train_forecaster
from benchmark_frozen_attention_timelines import canonical
from benchmark_exploration_aware_attention import SEED_OFFSET

SCHEMA="hearthbound.forecast-policy-stress.v1"
SCHEDULES=("permanent_depletion","bursty_mutations","long_observation_gaps")
LENGTH=64
SOURCES=4
STEPS_PER_SCHEDULE=24

def make_stress_timeline(seed,schedule,horizon=LENGTH):
    if (type(seed)!=int or seed<0 or schedule not in SCHEDULES
        or type(horizon)!=int or horizon<32 or horizon>128):
        raise ValueError("invalid out-of-distribution timeline")
    rng=random.Random(seed)
    # These processes and their constants are fixed before holdout evaluation.
    states=[]
    if schedule=="permanent_depletion":
        # Each resource starts stocked and permanently depletes at an
        # independent unseen time. There are no later restocks.
        depletion=[rng.randrange(8,horizon-8) for _ in range(SOURCES)]
        for t in range(horizon):
            states.append([int(t<depletion[s]) for s in range(SOURCES)])
    elif schedule=="bursty_mutations":
        # Rare bursts of elevated changes, with source-specific burst
        # intervals. The entire world changes independently of inspections.
        current=[rng.randrange(2) for _ in range(SOURCES)]
        burst_start=[rng.randrange(4,horizon-12) for _ in range(SOURCES)]
        for t in range(horizon):
            if t:
                for s in range(SOURCES):
                    in_burst=burst_start[s]<=t<burst_start[s]+10
                    if rng.random() < (.66 if in_burst else .012):
                        current[s]=1-current[s]
            states.append(current[:])
    else:
        # Long inactivity punctuated by rare, unannounced resource changes.
        # Inspection opportunities continue, but most source states remain
        # unchanged over tens of decisions.
        current=[rng.randrange(2) for _ in range(SOURCES)]
        change_at=[rng.randrange(20,horizon-8) for _ in range(SOURCES)]
        for t in range(horizon):
            if t:
                for s in range(SOURCES):
                    if t==change_at[s]: current[s]=1-current[s]
            states.append(current[:])
    transitions=[sum(a!=b for a,b in zip(states[t-1],states[t]))
                 for t in range(1,horizon)]
    out={
        "schema":"hearthbound.fixed-latent-source-trajectory.v1",
        "origin":"SIMULATED_ONLY",
        "seed":seed,"regime":schedule,
        "world_updates_per_inspection":1,
        "states":states,
        "latent_change_counts_between_decisions":transitions,
        "policy_generated_states":False,
        "policy_visible_future_states":False}
    out["sha256"]=hashlib.sha256(canonical(out).encode()).hexdigest()
    return out

def benchmark(training_seeds=(11,17,23),train_episodes=180,heldout=STEPS_PER_SCHEDULE):
    if (not training_seeds or len(set(training_seeds))!=len(training_seeds)
        or any(type(s)!=int or s<0 for s in training_seeds)
        or type(train_episodes)!=int or train_episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid stress evaluation budget")
    results=[]
    model_hashes={}
    for seed in training_seeds:
        # Same frozen forecaster trained by the PR #169 supervised objective.
        # The new dynamics are deliberately NEVER seen during training.
        model,training_labels=train_forecaster(seed+101,train_episodes)
        weights={name:np.asarray(v).tolist()
                 for name,v in sorted(model.params.items())}
        digest=hashlib.sha256(canonical(weights).encode()).hexdigest()
        model_hashes[str(seed)]=digest
        for index,schedule in enumerate(SCHEDULES):
            scores={name:[] for name in ARMS}
            minimums={name:[] for name in ARMS}
            deviations={name:[] for name in ARMS}
            hashes=[]
            for episode_id in range(heldout):
                timeline=make_stress_timeline(
                    SEED_OFFSET+seed*100000+index*10000+episode_id,schedule)
                hashes.append(timeline["sha256"])
                observations=episode(timeline,model)
                for name in ARMS:
                    scores[name].append(observations[name]["direct_discoveries"])
                    minimums[name].append(observations[name]["minimum_source_visits"])
                    deviations[name].append(observations[name][
                        "choices_different_from_scripted_fallback"])
            results.append({
                "train_seed":seed,"schedule":schedule,
                "timeline_length":LENGTH,"heldout_episodes":heldout,
                "frozen_forecaster_sha256":digest,
                "shared_latent_manifest_sha256":hashlib.sha256(
                    canonical(hashes).encode()).hexdigest(),
                "mean_direct_discoveries":{
                    arm:round(statistics.mean(scores[arm]),6) for arm in ARMS},
                "mean_min_source_visits":{
                    arm:round(statistics.mean(minimums[arm]),6) for arm in ARMS},
                "mean_deviations":{
                    arm:round(statistics.mean(deviations[arm]),6) for arm in ARMS},
                "mean_difference_from_scripted":{
                    arm:round(statistics.mean(a-b for a,b in
                        zip(scores[arm],scores["scripted"])),6)
                    for arm in ARMS if arm!="scripted"},
                # These direct paired differences permit independent CIs
                # without inventing latent-source observations.
                "paired_discovery_differences":{
                    arm:[a-b for a,b in zip(scores[arm],scores["scripted"])]
                    for arm in ARMS if arm!="scripted"}})
    report={
        "schema":SCHEMA,"origin":"SIMULATED_ONLY_OUT_OF_DISTRIBUTION",
        "training_seeds":list(training_seeds),
        "train_episodes_per_seed":train_episodes,
        "heldout_episodes_per_schedule_seed":heldout,
        "stress_schedules":list(SCHEDULES),
        "timeline_length":LENGTH,
        "frozen_forecaster_hashes":model_hashes,
        "same_frozen_model_per_seed_across_all_arms":True,
        "same_hidden_timeline_per_episode_across_all_arms":True,
        "stress_schedules_used_in_training":False,
        "observation_only_selected_source":True,
        "real_forge_outcomes_used_for_training":False,
        "new_weights_deployed_to_minecraft":False,
        "minecraft_model_promotion_authorized":False,
        "statistical_significance_claimed":False,
        "results":results}
    report["sha256"]=hashlib.sha256(canonical(report).encode()).hexdigest()
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",nargs="+",type=int,default=[11,17,23])
    p.add_argument("--episodes",type=int,default=180)
    p.add_argument("--heldout",type=int,default=STEPS_PER_SCHEDULE)
    p.add_argument("--output",type=Path,default=Path("forecast-policy-stress.json"))
    a=p.parse_args()
    result=benchmark(tuple(a.seeds),a.episodes,a.heldout)
    a.output.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n")
    print("FORECAST_POLICY_STRESS cells="+str(len(result["results"]))+
          " new_minecraft_weights=false")

if __name__=="__main__":
    main()
