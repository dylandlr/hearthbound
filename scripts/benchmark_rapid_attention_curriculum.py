#!/usr/bin/env python3
"""Simulator-only curriculum for rapid four-source selective attention.

Never uses RCON, actual Forge outcomes, privileged source truth as model input,
or unselected counterfactual rewards for training. Ground-truth simulator
state may be used for the *offline evaluation* of synthetic missed transitions.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path
import evaluate_causal_attention_history as causal
from train_simulated_attention_mlp import MLP,learned,scripted,SOURCES

SCHEMA="hearthbound.rapid-attention-curriculum.v1"
TRAIN_REGIMES=("in_distribution","unequal_volatility","high_volatility")
HELDOUT_REGIMES=("in_distribution","low_volatility","unequal_volatility","high_volatility")
HORIZON=32

class RapidWorld(causal.HistoricalWorld):
    def __init__(self,seed,regime,steps_per_inspection):
        if type(steps_per_inspection)!=int or not 1<=steps_per_inspection<=8:
            raise ValueError("invalid dynamics rate")
        super().__init__(seed,regime)
        self.steps_per_inspection=steps_per_inspection
        self.latent_transitions=0

    def inspect(self,source):
        # Inspect only the selected source. Its reward is computed from a
        # visible change since its prior DIRECT inspection, never from the
        # current states of unselected sources.
        before=self.memory[source]
        observed=self.truth[source]
        discovered=before==-1 or observed!=before
        reward=(1.0 if discovered else 0.)-.04
        if self.last_observation[source]!=-1 and self.last_observation[source]!=observed:
            self.observed_changes[source]+=1
        self.observed_count[source]+=1
        self.last_observation[source]=observed
        self.memory[source]=observed
        self.ages[source]=0
        for i in range(SOURCES):
            if i!=source:self.ages[i]=min(self.ages[i]+1,20)
        self.step_count+=1
        # Intervening changes occur after the selected observation; multiple
        # hidden flips between visits are not assumed to be witnessed.
        for _ in range(self.steps_per_inspection):
            for i in range(SOURCES):
                if self.rng.random()<self.volatility[i]:
                    self.truth[i]=1-self.truth[i]
                    self.latent_transitions+=1
        return reward,discovered

def train(seed,episodes,mixed):
    if type(episodes)!=int or episodes<1:
        raise ValueError("invalid training episode budget")
    model=MLP(seed)
    rng=random.Random(seed+7701)
    for e in range(episodes):
        regime=(TRAIN_REGIMES[e%len(TRAIN_REGIMES)] if mixed else "in_distribution")
        rate=(1,2,4)[(e//len(TRAIN_REGIMES))%3] if mixed else 1
        world=RapidWorld(2000000+seed*100000+e,regime,rate)
        epsilon=.08+.72*max(0.,1.-e/max(1.,episodes*.8))
        for _ in range(HORIZON):
            features=world.features()
            choice=(rng.randrange(SOURCES) if rng.random()<epsilon
                    else learned(model,world))
            reward,_=world.inspect(choice)
            model.update(features,choice,reward)
    return model

def evaluate(model,seed,regime,rate,episodes):
    differences=[]
    scripted_total=0
    neural_total=0
    for k in range(episodes):
        trial_seed=90000000+seed*100000+k
        baseline=RapidWorld(trial_seed,regime,rate)
        neural=RapidWorld(trial_seed,regime,rate)
        b=n=0
        for _ in range(HORIZON):
            _,found=baseline.inspect(scripted(baseline))
            b+=int(found)
            _,found=neural.inspect(learned(model,neural))
            n+=int(found)
        scripted_total+=b
        neural_total+=n
        differences.append(n-b)
    return {"scripted_mean_direct_discoveries":round(scripted_total/episodes,5),
            "neural_mean_direct_discoveries":round(neural_total/episodes,5),
            "mean_neural_minus_scripted_direct_discoveries":
                round(sum(differences)/episodes,5),
            "paired_episode_differences":differences}

def benchmark(seed=11,train_episodes=240,heldout=40):
    if (type(seed)!=int or seed<0 or type(heldout)!=int or heldout<1):
        raise ValueError("invalid evaluation configuration")
    models={"legacy_style":train(seed,train_episodes,False),
            "mixed_rapid_curriculum":train(seed+1,train_episodes,True)}
    results=[]
    for regime in HELDOUT_REGIMES:
        for rate in (1,2,4):
            rows={"regime":regime,"world_updates_per_inspection":rate,
                  "heldout_episodes":heldout}
            for name,model in models.items():
                result=evaluate(model,seed+100,regime,rate,heldout)
                # Keep aggregated outcome metrics only; never fabricate real
                # Forge reward or action attribution.
                rows[name]={k:v for k,v in result.items()
                            if k!="paired_episode_differences"}
            results.append(rows)
    report={"schema":SCHEMA,"origin":"SIMULATED_ONLY",
            "training_seed":seed,"train_episodes_per_model":train_episodes,
            "heldout_episodes_per_regime":heldout,
            "policy_input":"CAUSAL_DIRECT_OBSERVATION_HISTORY",
            "true_volatility_input_to_policy":False,
            "unselected_truth_input_to_policy":False,
            "training_reward":"SELECTED_SOURCE_DIRECT_OBSERVATION_CHANGE_ONLY",
            "real_forge_measurement_used":False,
            "minecraft_training_performed":False,
            "minecraft_policy_deployed":False,
            "model_replacement_authorized":False,
            "multi_seed_generalization_claimed":False,
            "results":results}
    report["sha256"]=hashlib.sha256(json.dumps(report,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--seed",type=int,default=11)
    parser.add_argument("--episodes",type=int,default=240)
    parser.add_argument("--heldout",type=int,default=40)
    parser.add_argument("--output",type=Path,default=Path("rapid-attention-curriculum.json"))
    args=parser.parse_args()
    report=benchmark(args.seed,args.episodes,args.heldout)
    args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("SIMULATED_RAPID_ATTENTION_CURRICULUM cases="+str(len(report["results"]))+
          " forge_execution=false model_replacement=false")

if __name__=="__main__":
    main()
