#!/usr/bin/env python3
"""Policy-independent synthetic resource timelines for paired attention tests.

Every policy receives the same hidden resource trajectory, pre-generated
before its first action. Only the inspected source at the current time enters
the policy's observation history. Not Minecraft, not online learning.
"""
import argparse
import hashlib
import json
import random
import statistics
from pathlib import Path

from benchmark_rapid_attention_curriculum import RapidWorld,HELDOUT_REGIMES
from benchmark_exploration_aware_attention import train_exploration,SEED_OFFSET,RATES
from benchmark_observed_uncertainty_objective import train_objective
from benchmark_history_gated_attention import gate
from train_simulated_attention_mlp import SOURCES,scripted,learned

SCHEMA="hearthbound.frozen-attention-timelines.v1"
HORIZON=32
ARMS=("scripted","exploration_neural","history_gated","uncertainty_neural")

def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),allow_nan=False)

def make_timeline(seed,regime,rate,horizon=HORIZON):
    if (type(seed)!=int or seed<0 or regime not in HELDOUT_REGIMES
        or type(rate)!=int or rate not in RATES
        or type(horizon)!=int or horizon<1):
        raise ValueError("invalid immutable trajectory specification")
    # Use existing regime definitions but generate all future changes in
    # advance. No policy can affect random draws, states or change timing.
    world=RapidWorld(seed,regime,rate)
    truth=tuple(world.truth)
    states=[truth]
    transitions=[]
    for _ in range(horizon-1):
        n=0
        for _ in range(rate):
            next_truth=list(truth)
            for source in range(SOURCES):
                if world.rng.random()<world.volatility[source]:
                    next_truth[source]=1-next_truth[source]
                    n+=1
            truth=tuple(next_truth)
        transitions.append(n)
        states.append(truth)
    result={"schema":"hearthbound.fixed-latent-source-trajectory.v1",
            "origin":"SIMULATED_ONLY",
            "seed":seed,"regime":regime,
            "world_updates_per_inspection":rate,
            "states":[list(x) for x in states],
            "latent_change_counts_between_decisions":transitions,
            "policy_generated_states":False,
            "policy_visible_future_states":False}
    result["sha256"]=hashlib.sha256(canonical(result).encode()).hexdigest()
    return result

class FrozenWorld:
    def __init__(self,timeline):
        if (timeline.get("schema")!="hearthbound.fixed-latent-source-trajectory.v1"
            or timeline.get("origin")!="SIMULATED_ONLY"
            or timeline.get("policy_generated_states") is not False
            or timeline.get("policy_visible_future_states") is not False
            or timeline.get("sha256")!=hashlib.sha256(canonical(
                {k:v for k,v in timeline.items() if k!="sha256"}).encode()).hexdigest()):
            raise ValueError("invalid frozen timeline")
        states=timeline["states"]
        if (not states or any(len(row)!=SOURCES or
             any(type(s)!=int or s not in (0,1) for s in row) for row in states)
            or len(timeline["latent_change_counts_between_decisions"])!=len(states)-1):
            raise ValueError("invalid latent source states")
        self._states=tuple(tuple(s) for s in states)
        self._time=0
        self.memory=[-1]*SOURCES
        self.ages=[20]*SOURCES
        self.observed_count=[0]*SOURCES
        self.observed_changes=[0]*SOURCES
        self.last_observation=[-1]*SOURCES

    def features(self):
        values=[]
        for source in range(SOURCES):
            n=self.observed_count[source]
            observed_rate=(self.observed_changes[source]/max(1,n-1)
                           if n>1 else .5)
            values.extend((
                float(self.memory[source]==-1),
                float(self.memory[source]==1),
                min(self.ages[source],20)/20.,
                observed_rate))
        return values

    def inspect(self,source):
        if (type(source)!=int or not 0<=source<SOURCES
            or self._time>=len(self._states)):
            raise ValueError("invalid selected source or exhausted timeline")
        # THIS is the only access to hidden truth during evaluation.
        observed=self._states[self._time][source]
        old=self.memory[source]
        discovered=old==-1 or old!=observed
        if self.last_observation[source]!=-1 and observed!=self.last_observation[source]:
            self.observed_changes[source]+=1
        self.observed_count[source]+=1
        self.last_observation[source]=observed
        for i in range(SOURCES):
            if i!=source:self.ages[i]=min(20,self.ages[i]+1)
        self.memory[source]=observed
        self.ages[source]=0
        self._time+=1
        return (1. if discovered else 0.)-.04,discovered

def replay(timeline,models):
    outcomes={}
    for arm in ARMS:
        world=FrozenWorld(timeline)
        discoveries=0
        choices=[]
        neural_count=0
        consecutive=0
        for _ in range(len(timeline["states"])):
            if arm=="scripted":
                action=scripted(world);neural=False
            elif arm=="history_gated":
                action,neural=gate(world,models["exploration_neural"],consecutive)
            else:
                action=learned(models[arm],world);neural=True
            # Policy decisions are computed without a reference to timeline.
            consecutive=consecutive+1 if neural else 0
            neural_count+=int(neural)
            choices.append(action)
            _,discovered=world.inspect(action)
            discoveries+=int(discovered)
        outcomes[arm]={
            "direct_discoveries":discoveries,
            "neural_choices":neural_count,
            "source_visits":[choices.count(i) for i in range(SOURCES)]}
    return outcomes

def benchmark(train_seeds=(11,17,23),episodes=240,heldout=40):
    if (not train_seeds or len(set(train_seeds))!=len(train_seeds)
        or any(type(x)!=int or x<0 for x in train_seeds)
        or type(episodes)!=int or episodes<1
        or type(heldout)!=int or heldout<1):
        raise ValueError("invalid training/evaluation budget")
    cases=[]
    for train_seed in train_seeds:
        models={"exploration_neural":train_exploration(train_seed+2,episodes),
                "uncertainty_neural":train_objective(train_seed+3,episodes)}
        for regime_index,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                scores={arm:[] for arm in ARMS}
                diversity={arm:[] for arm in ARMS}
                timeline_hashes=[]
                for ep in range(heldout):
                    seed=SEED_OFFSET+train_seed*100000+regime_index*10000+rate*1000+ep
                    timeline=make_timeline(seed,regime,rate)
                    timeline_hashes.append(timeline["sha256"])
                    output=replay(timeline,models)
                    for arm in ARMS:
                        scores[arm].append(output[arm]["direct_discoveries"])
                        diversity[arm].append(min(output[arm]["source_visits"]))
                baseline=scores["scripted"]
                cases.append({
                    "train_seed":train_seed,
                    "regime":regime,
                    "world_updates_per_inspection":rate,
                    "heldout_episodes":heldout,
                    "shared_timeline_digest":hashlib.sha256(
                        canonical(timeline_hashes).encode()).hexdigest(),
                    "mean_direct_discoveries":{
                        arm:round(statistics.mean(scores[arm]),5) for arm in ARMS},
                    "mean_minimum_source_visits":{
                        arm:round(statistics.mean(diversity[arm]),5) for arm in ARMS},
                    "neural_minus_scripted_mean":{
                        arm:round(statistics.mean(a-b for a,b in zip(scores[arm],baseline)),5)
                        for arm in ARMS if arm!="scripted"}})
    summary={}
    for arm in ARMS[1:]:
        byregime={}
        for regime in HELDOUT_REGIMES:
            subset=[case["neural_minus_scripted_mean"][arm] for case in cases
                    if case["regime"]==regime]
            byregime[regime]=round(statistics.mean(subset),5)
        summary[arm]={"regime_mean_differences":byregime,
                      "overall_mean_difference":round(statistics.mean(
                          c["neural_minus_scripted_mean"][arm] for c in cases),5),
                      "negative_seed_regime_rate_cells":sum(
                          c["neural_minus_scripted_mean"][arm]<0 for c in cases)}
    report={
        "schema":SCHEMA,"origin":"SIMULATED_ONLY_POLICY_INDEPENDENT_TRAJECTORIES",
        "training_seeds":list(train_seeds),
        "train_episodes_per_model":episodes,
        "heldout_episodes_per_cell":heldout,
        "trajectory_generation":"PREGENERATED_BEFORE_ALL_POLICY_CHOICES",
        "all_arms_share_identical_latent_trajectories":True,
        "resource_timeline_visible_to_policy":False,
        "policy_observation_only_selected_source":True,
        "hidden_truth_or_unselected_rewards_used_for_training":False,
        "minecraft_policy_deployed":False,
        "model_promotion_authorized":False,
        "real_forge_performance_claimed":False,
        "cases":cases,"summary":summary}
    report["sha256"]=hashlib.sha256(canonical(report).encode()).hexdigest()
    return report

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--seeds",nargs="+",type=int,default=[11,17,23])
    cli.add_argument("--episodes",type=int,default=240)
    cli.add_argument("--heldout",type=int,default=40)
    cli.add_argument("--output",type=Path,default=Path("frozen-attention-timelines.json"))
    args=cli.parse_args()
    report=benchmark(tuple(args.seeds),args.episodes,args.heldout)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    print("FROZEN_ATTENTION_TIMELINE_BENCHMARK cases="+str(len(report["cases"]))+
          " identical_latent_trajectories=true promotion=false")
if __name__=="__main__":
    main()
