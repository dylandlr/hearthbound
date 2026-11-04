#!/usr/bin/env python3
"""Causal observation-history attention experiment; simulator-only.

Hidden source truth and true resource volatility never enter policy features.
The fourth feature is an empirical rate from *observed* changes; observing the
same source twice across many ticks is not assumed to reveal intermediate flips.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

import train_simulated_attention_mlp as baseline
from evaluate_simulated_attention_robustness import interval

SCHEMA="hearthbound.causal-attention-history.v1"
REGIMES=("in_distribution","high_volatility","low_volatility","unequal_volatility")
HORIZON=32

class HistoricalWorld(baseline.World):
    def __init__(self, seed, regime="in_distribution"):
        super().__init__(seed)
        self.regime=regime
        if regime=="high_volatility":
            self.volatility=[min(.95,v*2.) for v in self.volatility]
        elif regime=="low_volatility":
            self.volatility=[max(.005,v*.25) for v in self.volatility]
        elif regime=="unequal_volatility":
            self.volatility=[.015,.08,.45,.9]
        elif regime!="in_distribution":
            raise ValueError("unknown regime")
        self.observed_count=[0]*baseline.SOURCES
        self.observed_changes=[0]*baseline.SOURCES
        self.last_observation=[-1]*baseline.SOURCES

    def features(self):
        result=[]
        for i in range(baseline.SOURCES):
            # The empirical change frequency is calculated from previous
            # inspections only. It is not the true per-tick flip probability.
            history=(self.observed_changes[i]/max(1,self.observed_count[i]-1)
                     if self.observed_count[i]>1 else .5)
            result.extend((
                float(self.memory[i]==-1),
                float(self.memory[i]==1),
                min(self.ages[i],20)/20.,
                history))
        return result

    def inspect(self,source):
        if not 0<=source<baseline.SOURCES:
            raise ValueError("invalid source")
        # The selected sensor is the only legitimate point to reveal truth.
        observation=self.truth[source]
        if self.last_observation[source]!=-1 and observation!=self.last_observation[source]:
            self.observed_changes[source]+=1
        self.observed_count[source]+=1
        self.last_observation[source]=observation
        return super().inspect(source)

def train(seed, episodes):
    model=baseline.MLP(seed)
    rng=random.Random(seed+7)
    for episode in range(episodes):
        world=HistoricalWorld(1000000+seed*100000+episode)
        epsilon=.08+.75*max(0.,1.-episode/max(1,episodes*.8))
        for _ in range(HORIZON):
            x=world.features()
            decision=(rng.randrange(baseline.SOURCES) if rng.random()<epsilon
                      else baseline.learned(model,world))
            reward,_=world.inspect(decision)
            model.update(x,decision,reward)
    return model

def episode(seed,regime,policy,model):
    world=HistoricalWorld(seed,regime)
    discoveries=0
    total=0.
    selected=[0]*baseline.SOURCES
    for _ in range(HORIZON):
        choice=(baseline.scripted(world) if policy=="scripted"
                else baseline.learned(model,world))
        selected[choice]+=1
        reward,found=world.inspect(choice)
        discoveries+=int(found)
        total+=reward
    return discoveries,round(total,8),selected

def benchmark(train_seeds=(11,17,23),train_episodes=500,
              eval_episodes=100,bootstrap_replicates=300):
    if not train_seeds or len(set(train_seeds))!=len(train_seeds) or train_episodes<1 or eval_episodes<1 or bootstrap_replicates<10:
        raise ValueError("invalid evaluation budget")
    results=[]
    for train_seed in train_seeds:
        model=train(train_seed,train_episodes)
        for regime_id,regime in enumerate(REGIMES):
            differences=[]
            scripted_scores=[]
            trained_scores=[]
            for k in range(eval_episodes):
                world_seed=90000000+train_seed*100000+k
                scripted,_,_=episode(world_seed,regime,"scripted",model)
                learned,_,_=episode(world_seed,regime,"learned",model)
                differences.append(learned-scripted)
                scripted_scores.append(scripted)
                trained_scores.append(learned)
            results.append({
                "train_seed":train_seed,
                "regime":regime,
                "scripted_mean_discoveries":round(sum(scripted_scores)/eval_episodes,6),
                "causal_mlp_mean_discoveries":round(sum(trained_scores)/eval_episodes,6),
                "paired_discovery_difference":interval(
                    differences,train_seed*100+regime_id,bootstrap_replicates)
            })
    output={
        "schema":SCHEMA,
        "origin":"SIMULATED_ONLY",
        "feature_names_per_source":[
            "never_inspected","last_observed_available","observation_age_norm",
            "empirical_change_frequency_from_observations"],
        "privileged_volatility_feature":False,
        "true_source_availability_visible_to_policy":False,
        "training_seeds":list(train_seeds),
        "train_episodes_per_seed":train_episodes,
        "heldout_episodes_per_seed_regime":eval_episodes,
        "bootstrap_replicates":bootstrap_replicates,
        "observations_per_decision":1,
        "minecraft_policy_deployed":False,
        "minecraft_learning_claimed":False,
        "citizen_actions_authorized":False,
        "results":results,
        "limitations":[
            "Synthetic latent resource dynamics, not Minecraft outcomes",
            "Change frequency measures differences between observations, not all intervening world changes",
            "Bootstrap confidence intervals account for episodes within one training seed only",
            "No visual line of sight, navigation, execution or social interactions",
            "Performance still requires comparison with a held-out real Forge timeline"
        ]
    }
    canonical=json.dumps(output,sort_keys=True,separators=(",",":"),allow_nan=False)
    output["sha256"]=hashlib.sha256(canonical.encode()).hexdigest()
    return output

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seeds",type=int,nargs="+",default=[11,17,23])
    parser.add_argument("--train-episodes",type=int,default=500)
    parser.add_argument("--heldout",type=int,default=100)
    parser.add_argument("--bootstrap",type=int,default=300)
    parser.add_argument("--output",type=Path,default=Path("causal-attention-history.json"))
    args=parser.parse_args()
    report=benchmark(tuple(args.seeds),args.train_episodes,args.heldout,args.bootstrap)
    args.output.write_text(json.dumps(report,sort_keys=True,indent=2)+"\n")
    for record in report["results"]:
        delta=record["paired_discovery_difference"]
        print("CAUSAL_ATTENTION", "seed="+str(record["train_seed"]),
              "regime="+record["regime"],
              "delta="+str(delta["mean"]),
              "ci="+str(delta["bootstrap_95_ci"]),
              "origin=SIMULATED_ONLY")
    print("CAUSAL_ATTENTION_COMPLETE sha256="+report["sha256"])

if __name__=="__main__":
    main()
