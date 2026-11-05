#!/usr/bin/env python3
"""Policy-only study with frozen selected-source GRU change forecasts.

Train one recurrent forecaster per training seed, then share its exact frozen
weights across all policies. Synthetic hidden timelines are pre-generated and
identical for each evaluated policy. No new predictor training or Forge access.
"""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np

from benchmark_observed_change_forecast import (
    train as train_forecaster, sigmoid_scalar, history_input, forecast_policy)
from benchmark_frozen_attention_timelines import make_timeline,FrozenWorld,canonical
from benchmark_rapid_attention_curriculum import HELDOUT_REGIMES
from benchmark_exploration_aware_attention import SEED_OFFSET,RATES
from train_simulated_attention_mlp import SOURCES,scripted
from benchmark_recurrent_causal_attention import HIDDEN

SCHEMA="hearthbound.forecast-policy-gating.v1"
HORIZON=32
ARMS=("scripted","greedy_forecast","age_blend","coverage_guard")
AGE_WEIGHT=.35
MIN_DIRECT_OBSERVATIONS=2
FORECAST_SPREAD_THRESHOLD=.20
MAX_SAME_SOURCE_STREAK=2

def select(world,probabilities,arm,last_choice=None,streak=0):
    if arm not in ARMS or type(streak)!=int or streak<0:
        raise ValueError("unknown decision rule or invalid streak")
    if len(probabilities)!=SOURCES or not all(
            isinstance(p,(float,int)) and math.isfinite(p) and 0<=p<=1
            for p in probabilities):
        raise ValueError("invalid forecaster output")
    if last_choice is not None and (
            type(last_choice)!=int or last_choice not in range(SOURCES)):
        raise ValueError("invalid previous choice")
    fallback=scripted(world)
    if arm=="scripted":
        return fallback,False
    if arm=="greedy_forecast":
        choice=forecast_policy(world,probabilities)
        return choice,choice!=fallback
    if min(world.observed_count)<MIN_DIRECT_OBSERVATIONS:
        return fallback,False
    if arm=="age_blend":
        # Fixed blend; ages come from the citizen's own direct observations.
        score=lambda i:(1-AGE_WEIGHT)*probabilities[i]+AGE_WEIGHT*min(
            world.ages[i],20)/20.
        choice=max(range(SOURCES),key=lambda i:(score(i),world.ages[i],-i))
    else:
        # Use neural prioritization only when differences in directly
        # predicted change probability are large enough to justify diversion.
        if max(probabilities)-min(probabilities)<FORECAST_SPREAD_THRESHOLD:
            return fallback,False
        choice=max(range(SOURCES),key=lambda i:(
            probabilities[i],world.ages[i],-i))
        if choice==last_choice and streak>=MAX_SAME_SOURCE_STREAK:
            return fallback,False
    return choice,choice!=fallback

def episode(timeline,model):
    results={}
    for arm in ARMS:
        world=FrozenWorld(timeline)
        hidden=np.zeros(HIDDEN)
        last_action=None
        last_discovery=last_available=0
        streak=0
        decisions=0
        counts=[0]*SOURCES
        witnessed=0
        for _ in timeline["states"]:
            x=history_input(world,last_action,last_discovery,last_available)
            # Same frozen model. Only the agent's action-dependent private
            # observation history and resulting recurrent state may differ.
            logits,hidden,_=model.step(x,hidden)
            probabilities=[sigmoid_scalar(s) for s in logits]
            action,deviation=select(world,probabilities,arm,last_action,streak)
            streak=streak+1 if action==last_action else 1
            decisions+=int(deviation)
            counts[action]+=1
            _,found=world.inspect(action)
            witnessed+=int(found)
            last_action=action
            last_discovery=int(found)
            last_available=int(world.memory[action]==1)
        results[arm]={
            "direct_discoveries":witnessed,
            "minimum_source_visits":min(counts),
            "distinct_sources":sum(x>0 for x in counts),
            "choices_different_from_scripted_fallback":decisions}
    return results

def benchmark(seeds=(11,17,23),train_episodes=180,heldout=24):
    if (not seeds or len(set(seeds))!=len(seeds)
        or any(type(x)!=int or x<0 for x in seeds)
        or type(train_episodes)!=int or train_episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid forecast policy study budget")
    rows=[]
    model_digests={}
    for training_seed in seeds:
        # One and only one fitted forecaster for every rule and test regime.
        model,labels=train_forecaster(training_seed+101,train_episodes)
        weight_payload={k:np.asarray(v).tolist()
                        for k,v in sorted(model.params.items())}
        model_sha=hashlib.sha256(canonical(weight_payload).encode()).hexdigest()
        model_digests[str(training_seed)]=model_sha
        for regime_id,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                scores={name:[] for name in ARMS}
                minimums={name:[] for name in ARMS}
                deviations={name:[] for name in ARMS}
                timeline_digests=[]
                for i in range(heldout):
                    seed=(SEED_OFFSET+training_seed*100000
                          +regime_id*10000+rate*1000+i)
                    timeline=make_timeline(seed,regime,rate)
                    timeline_digests.append(timeline["sha256"])
                    outcome=episode(timeline,model)
                    for arm in ARMS:
                        scores[arm].append(outcome[arm]["direct_discoveries"])
                        minimums[arm].append(outcome[arm]["minimum_source_visits"])
                        deviations[arm].append(
                            outcome[arm]["choices_different_from_scripted_fallback"])
                rows.append({
                    "training_seed":training_seed,
                    "regime":regime,
                    "updates_per_inspection":rate,
                    "heldout_episodes":heldout,
                    "frozen_model_sha256":model_sha,
                    "training_direct_reinspection_labels":labels,
                    "shared_latent_manifest_sha256":hashlib.sha256(
                        canonical(timeline_digests).encode()).hexdigest(),
                    "mean_direct_discoveries":{
                        arm:round(statistics.mean(scores[arm]),6) for arm in ARMS},
                    "mean_minimum_source_visits":{
                        arm:round(statistics.mean(minimums[arm]),6) for arm in ARMS},
                    "mean_policy_deviations_from_scripted":{
                        arm:round(statistics.mean(deviations[arm]),6) for arm in ARMS},
                    "mean_vs_scripted":{
                        arm:round(statistics.mean(a-b for a,b in
                            zip(scores[arm],scores["scripted"])),6)
                        for arm in ARMS if arm!="scripted"}})
    summary={}
    for arm in ARMS[1:]:
        overall=[r["mean_vs_scripted"][arm] for r in rows]
        summary[arm]={
            "overall_mean_delta":round(statistics.mean(overall),6),
            "negative_seed_regime_rate_cases":sum(x<0 for x in overall),
            "regime_means":{
                regime:round(statistics.mean(
                    r["mean_vs_scripted"][arm] for r in rows
                    if r["regime"]==regime),6)
                for regime in HELDOUT_REGIMES},
            "training_seed_means":{
                str(s):round(statistics.mean(
                    r["mean_vs_scripted"][arm] for r in rows
                    if r["training_seed"]==s),6)
                for s in seeds}}
    result={
        "schema":SCHEMA,"origin":"SIMULATED_ONLY",
        "training_seeds":list(seeds),
        "train_episodes_per_seed":train_episodes,
        "heldout_episodes_per_cell":heldout,
        "model_hashes_by_training_seed":model_digests,
        "rule_thresholds":{
            "age_weight":AGE_WEIGHT,
            "min_direct_observations_per_source":MIN_DIRECT_OBSERVATIONS,
            "minimum_probability_spread":FORECAST_SPREAD_THRESHOLD,
            "max_same_source_streak":MAX_SAME_SOURCE_STREAK},
        "same_frozen_forecaster_for_every_policy_per_seed":True,
        "frozen_trajectories_shared_between_policies":True,
        "policy_can_access_unselected_source_truth":False,
        "unobserved_source_labels_used_for_training":False,
        "forge_model_changed":False,
        "minecraft_model_promotion_authorized":False,
        "statistical_significance_claimed":False,
        "cases":rows,"summary":summary}
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--seeds",nargs="+",type=int,default=[11,17,23])
    p.add_argument("--episodes",type=int,default=180)
    p.add_argument("--heldout",type=int,default=24)
    p.add_argument("--output",type=Path,default=Path("forecast-policy-gating.json"))
    args=p.parse_args()
    report=benchmark(tuple(args.seeds),args.episodes,args.heldout)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("FORECAST_POLICY_FROZEN_MODEL cases="+str(len(report["cases"]))+
          " model_promotion=false")

if __name__=="__main__":
    main()
