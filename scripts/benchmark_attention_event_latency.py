#!/usr/bin/env python3
"""Audit actual synthetic change detection timing without privileged agent input.

Per-policy source inspections are chosen using only citizen observation memory
and frozen GRU outputs. Separately, the evaluator matches actual latent state
transitions to a later direct reinspection before the next same-source change.
"""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np

from benchmark_forecast_policy_stress import (
    make_stress_timeline, SCHEDULES, LENGTH)
from benchmark_forecast_policy_gating import select, ARMS
from benchmark_observed_change_forecast import (
    train as train_forecaster, history_input, sigmoid_scalar)
from benchmark_frozen_attention_timelines import FrozenWorld, canonical
from benchmark_exploration_aware_attention import SEED_OFFSET
from benchmark_recurrent_causal_attention import HIDDEN,SOURCES

SCHEMA="hearthbound.attention-event-latency.v1"

def replay_observations(timeline,model,arm):
    if arm not in ARMS:
        raise ValueError("unknown attention policy")
    world=FrozenWorld(timeline)
    hidden=np.zeros(HIDDEN)
    last_action=None
    last_discovery=last_available=0
    streak=0
    observations=[]
    parameters_before={k:v.copy() for k,v in model.params.items()}
    for time in range(len(timeline["states"])):
        x=history_input(world,last_action,last_discovery,last_available)
        logits,hidden,_=model.step(x,hidden)
        probs=[sigmoid_scalar(logit) for logit in logits]
        selected,_=select(world,probs,arm,last_action,streak)
        before=world.memory[selected]
        _,discovered=world.inspect(selected)
        after=world.memory[selected]
        observations.append({
            "step":time,"selected_source":selected,
            "prior_direct_state":before,"observed_state":after,
            "first_inspection":before==-1,
            "direct_disagreement":bool(before!=-1 and before!=after),
            "direct_discovery":bool(discovered)})
        streak=streak+1 if selected==last_action else 1
        last_action=selected
        last_discovery=int(discovered)
        last_available=int(after==1)
    assert all(np.array_equal(model.params[k],v)
               for k,v in parameters_before.items())
    return observations

def analyze_events(timeline,observations):
    """Event detection is possible only after a direct pre-event baseline.

    A hidden source transition at step t is counted as witnessed if a policy
    inspected that source before t and next directly inspects it at some step
    k >= t and strictly BEFORE the next change of the same source.
    State reversals before inspection are therefore not falsely credited.
    """
    states=timeline["states"]
    if (len(observations)!=len(states) or any(
        obs.get("step")!=i or obs.get("selected_source") not in range(SOURCES)
        or obs.get("observed_state")!=states[i][obs["selected_source"]]
        for i,obs in enumerate(observations))):
        raise ValueError("invalid direct inspection journal")
    by_source={s:[] for s in range(SOURCES)}
    for obs in observations:
        by_source[obs["selected_source"]].append(obs)
    events=[]
    for source in range(SOURCES):
        changes=[t for t in range(1,len(states))
                 if states[t][source]!=states[t-1][source]]
        for index,step in enumerate(changes):
            next_change=(changes[index+1] if index+1<len(changes)
                         else len(states))
            before=[v for v in by_source[source] if v["step"]<step]
            after=[v for v in by_source[source]
                   if step<=v["step"]<next_change]
            is_baselined=bool(before)
            first_valid=(after[0] if after else None)
            witnessed=bool(is_baselined and first_valid and first_valid["direct_disagreement"])
            latency=(first_valid["step"]-step if witnessed else None)
            events.append({
                "source":source,"transition_step":step,
                "next_same_source_transition_step":next_change,
                "direct_baseline_known_before_change":is_baselined,
                "directly_witnessed_before_next_change":witnessed,
                "detection_delay_steps":latency})
    useful=sum(o["direct_disagreement"] for o in observations)
    known_reinspections=sum(not o["first_inspection"] for o in observations)
    latency_values=[e["detection_delay_steps"] for e in events
                    if e["directly_witnessed_before_next_change"]]
    verified_events=sum(e["directly_witnessed_before_next_change"] for e in events)
    eligible=sum(e["direct_baseline_known_before_change"] for e in events)
    # Censor missing events at the remaining evaluation horizon. All
    # policies share the same event times, so this supports paired comparison
    # without rewarding selective detection of easy events.
    censored_delays=[
        (e["detection_delay_steps"] if e["directly_witnessed_before_next_change"]
         else len(states)-e["transition_step"])
        for e in events]
    return {
        "latent_transition_count":len(events),
        "mean_censored_event_delay_steps":(
            None if not events else statistics.mean(censored_delays)),
        "total_censored_event_delay_steps":sum(censored_delays),
        "baseline_eligible_transitions":eligible,
        "transitions_witnessed_before_next_change":verified_events,
        "transitions_not_witnessed":len(events)-verified_events,
        "mean_detection_latency_steps":(
            None if not latency_values else statistics.mean(latency_values)),
        "total_detection_delay_steps":sum(latency_values),
        "direct_reinspection_disagreements":useful,
        "reinspection_count":known_reinspections,
        "unproductive_reinspections":known_reinspections-useful,
        "first_inspection_count":len(observations)-known_reinspections,
        "events":events}

def benchmark(seeds=(11,17,23),episodes=180,heldout=24):
    if (not seeds or len(set(seeds))!=len(seeds)
        or any(type(s)!=int or s<0 for s in seeds)
        or type(episodes)!=int or episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid event-latency study")
    cells=[]
    hashes={}
    for seed in seeds:
        model,_=train_forecaster(seed+101,episodes)
        weights={name:np.asarray(v).tolist()
                 for name,v in sorted(model.params.items())}
        digest=hashlib.sha256(canonical(weights).encode()).hexdigest()
        hashes[str(seed)]=digest
        for schedule_index,schedule in enumerate(SCHEDULES):
            totals={arm:[] for arm in ARMS}
            latent_hashes=[]
            for e in range(heldout):
                t=make_stress_timeline(
                    SEED_OFFSET+seed*100000+schedule_index*10000+e,schedule)
                latent_hashes.append(t["sha256"])
                arm_results={}
                for arm in ARMS:
                    log=replay_observations(t,model,arm)
                    arm_results[arm]=analyze_events(t,log)
                    # Hidden truth never enters the policy's observation
                    # or the model's training. The evaluation alone reads it.
                totals["scripted"].append(arm_results["scripted"])
                for arm in ARMS[1:]:
                    totals[arm].append(arm_results[arm])
            rows={}
            for arm in ARMS:
                parts=totals[arm]
                witnessed=[v["transitions_witnessed_before_next_change"] for v in parts]
                delays=[v["total_detection_delay_steps"] for v in parts]
                useful=[v["direct_reinspection_disagreements"] for v in parts]
                wasted=[v["unproductive_reinspections"] for v in parts]
                censored=[v["total_censored_event_delay_steps"] for v in parts]
                totals_events=[v["latent_transition_count"] for v in parts]
                rows[arm]={
                    "mean_latent_transition_count":round(statistics.mean(totals_events),6),
                    "mean_total_censored_event_delay":round(statistics.mean(censored),6),
                    "mean_witnessed_latent_events":round(statistics.mean(witnessed),6),
                    "mean_total_detection_delay":round(statistics.mean(delays),6),
                    "mean_direct_reinspection_disagreements":round(
                        statistics.mean(useful),6),
                    "mean_unproductive_reinspections":round(
                        statistics.mean(wasted),6)}
            pairs={
                arm:{
                    "witnessed_event_differences":[
                        a["transitions_witnessed_before_next_change"]
                        -b["transitions_witnessed_before_next_change"]
                        for a,b in zip(totals[arm],totals["scripted"])],
                    "censored_event_delay_differences":[
                        a["total_censored_event_delay_steps"]
                        -b["total_censored_event_delay_steps"]
                        for a,b in zip(totals[arm],totals["scripted"])],
                    "direct_reinspection_difference":[
                        a["direct_reinspection_disagreements"]
                        -b["direct_reinspection_disagreements"]
                        for a,b in zip(totals[arm],totals["scripted"])]}
                for arm in ARMS[1:]}
            cells.append({
                "training_seed":seed,"schedule":schedule,
                "heldout_episodes":heldout,"timeline_length":LENGTH,
                "frozen_model_sha256":digest,
                "shared_latent_manifest_sha256":hashlib.sha256(
                    canonical(latent_hashes).encode()).hexdigest(),
                "mean_by_arm":rows,
                "paired_against_scripted":pairs})
    out={
        "schema":SCHEMA,"origin":"SIMULATOR_ONLY_EVENT_JOURNAL_AUDIT",
        "train_seeds":list(seeds),"train_episodes_per_seed":episodes,
        "heldout_episodes_per_schedule":heldout,
        "schedules":list(SCHEDULES),
        "model_hashes":hashes,
        "event_match":"DIRECT_POST_TRANSITION_REINSPECTION_BEFORE_NEXT_SAME_SOURCE_CHANGE_WITH_PRETRANSITION_BASELINE",
        "missed_event_censoring":"REMAINING_HORIZON_STEPS_FROM_TRANSITION",
        "models_frozen_across_policies":True,
        "latent_world_sequences_identical_per_episode":True,
        "agent_can_read_hidden_transition_log":False,
        "event_outcomes_used_for_training":False,
        "minecraft_weights_promoted":False,
        "model_promotion_authorized":False,
        "cells":cells}
    out["sha256"]=hashlib.sha256(canonical(out).encode()).hexdigest()
    return out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",nargs="+",type=int,default=[11,17,23])
    parser.add_argument("--episodes",type=int,default=180)
    parser.add_argument("--heldout",type=int,default=24)
    parser.add_argument("--output",type=Path,default=Path("attention-event-latency.json"))
    args=parser.parse_args()
    out=benchmark(tuple(args.seeds),args.episodes,args.heldout)
    args.output.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n")
    print("EVENT_LATENCY_AUDIT cells="+str(len(out["cells"]))+
          " minecraft_model_promotion=false")

if __name__=="__main__":
    main()
