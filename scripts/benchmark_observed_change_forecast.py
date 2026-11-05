#!/usr/bin/env python3
"""Selected-only GRU resource-change forecasting, then separate policy evaluation.

Forecast target exists ONLY after directly inspecting a previously observed
source. Unselected sources receive neither training labels nor pseudo-labels.
All evaluation timelines are policy independent and simulator-only.
"""
import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
import numpy as np

from benchmark_recurrent_causal_attention import GRU,HIDDEN,SOURCES,history_input
from benchmark_gru_truncated_bptt import WINDOW
from benchmark_frozen_attention_timelines import make_timeline,FrozenWorld,canonical
from benchmark_exploration_aware_attention import SEED_OFFSET,RATES
from benchmark_rapid_attention_curriculum import HELDOUT_REGIMES,TRAIN_REGIMES
from train_simulated_attention_mlp import scripted

SCHEMA="hearthbound.observed-change-forecast.v1"
HORIZON=32
ARMS=("scripted","forecast_gated")
EVAL_EPSILON=.20

def sigmoid_scalar(s):
    return float(1./(1.+math.exp(-max(-35.,min(35.,float(s))))))

def history_baseline(world):
    """A source-specific observed-disagreement estimate, not true volatility."""
    results=[]
    for n,c in zip(world.observed_count,world.observed_changes):
        results.append((c+1)/(n+1) if n>=1 else .5)
    return results

def chosen_supervised_gradient(model,caches,actions,targets):
    """Backprop selected Bernoulli log-loss through a GRU sequence chunk.

    Mask first inspections and all other unobserved alternative source heads.
    """
    if not caches or len(caches)>WINDOW or not (
        len(caches)==len(actions)==len(targets)):
        raise ValueError("invalid sequence supervision")
    gradients={key:np.zeros_like(v) for key,v in model.params.items()}
    p=model.params
    upstream=np.zeros(HIDDEN)
    count=0
    for cache,action,target in reversed(list(zip(caches,actions,targets))):
        if type(action)!=int or action not in range(SOURCES):
            raise ValueError("invalid choice")
        x,old,z,r,n,h=cache
        if target is None:
            error=0.
        else:
            if type(target)!=int or target not in (0,1):
                raise ValueError("invalid witnessed binary change")
            score=float((p["Wo"]@h+p["bo"])[action])
            error=sigmoid_scalar(score)-target
            count+=1
        gradients["Wo"][action]+=error*h
        gradients["bo"][action]+=error
        dh=upstream+error*p["Wo"][action]
        dn_pre=dh*(1-z)*(1-n*n)
        dz_pre=dh*(old-n)*z*(1-z)
        drh=p["Un"].T@dn_pre
        dr_pre=drh*old*r*(1-r)
        gradients["Wn"]+=np.outer(dn_pre,x)
        gradients["Un"]+=np.outer(dn_pre,r*old)
        gradients["bn"]+=dn_pre
        gradients["Wz"]+=np.outer(dz_pre,x)
        gradients["Uz"]+=np.outer(dz_pre,old)
        gradients["bz"]+=dz_pre
        gradients["Wr"]+=np.outer(dr_pre,x)
        gradients["Ur"]+=np.outer(dr_pre,old)
        gradients["br"]+=dr_pre
        upstream=dh*z+drh*r+p["Uz"].T@dz_pre+p["Ur"].T@dr_pre
    return gradients,count

def update(model,gradients,count,rate=.020):
    if type(count)!=int or count<0:
        raise ValueError("invalid count")
    if not count:return
    norm=math.sqrt(sum(float(np.sum(v*v)) for v in gradients.values()))
    scale=rate*min(1.,3./max(1e-12,norm))/count
    for k in model.params:
        model.params[k]-=scale*gradients[k]

def train(seed,episodes=180):
    if type(seed)!=int or seed<0 or type(episodes)!=int or episodes<1:
        raise ValueError("invalid forecasting training budget")
    model=GRU(seed)
    rng=np.random.default_rng(seed+54013)
    witnessed_targets=0
    for e in range(episodes):
        regime=TRAIN_REGIMES[e%len(TRAIN_REGIMES)]
        rate=RATES[(e//len(TRAIN_REGIMES))%len(RATES)]
        world=FrozenWorld(make_timeline(2000000+seed*100000+e,regime,rate))
        hidden=np.zeros(HIDDEN)
        last_action=None
        last_discovery=last_available=0
        for _ in range(HORIZON//WINDOW):
            caches=[];actions=[];targets=[]
            for _ in range(WINDOW):
                x=history_input(world,last_action,last_discovery,last_available)
                _,next_hidden,cache=model.step(x,hidden)
                # Training probes are exogenous to predictions and use no
                # uninspected truth. Scripted rotation + randomized exploration.
                action=(int(rng.integers(SOURCES)) if rng.random()<EVAL_EPSILON
                        else scripted(world))
                previously_known=world.memory[action]!=-1
                _,discovered=world.inspect(action)
                target=int(discovered) if previously_known else None
                caches.append(cache);actions.append(action);targets.append(target)
                hidden=next_hidden
                last_action=action
                last_discovery=int(discovered)
                last_available=int(world.memory[action]==1)
            grads,count=chosen_supervised_gradient(model,caches,actions,targets)
            witnessed_targets+=count
            update(model,grads,count)
    return model,witnessed_targets

def forecast_policy(world,probabilities):
    # Minimum exploration is a pre-declared policy constraint. No hidden truth.
    if min(world.observed_count)<2:
        return scripted(world)
    if len(probabilities)!=SOURCES or not all(
        math.isfinite(p) and 0<=p<=1 for p in probabilities):
        raise ValueError("invalid predictions")
    return max(range(SOURCES),key=lambda i:(probabilities[i],world.ages[i],-i))

def probe_forecasts(timeline,model,seed):
    """Fixed exploration policy probes prediction accuracy without model choice."""
    world=FrozenWorld(timeline)
    rng=np.random.default_rng(seed+54017)
    hidden=np.zeros(HIDDEN)
    last_action=None
    last_discovery=last_available=0
    rows=[]
    for _ in timeline["states"]:
        x=history_input(world,last_action,last_discovery,last_available)
        scores,hidden,_=model.step(x,hidden)
        choice=(int(rng.integers(SOURCES)) if rng.random()<EVAL_EPSILON
                else scripted(world))
        prior=world.memory[choice]
        historical_probability=history_baseline(world)[choice]
        probability=sigmoid_scalar(scores[choice])
        _,discovered=world.inspect(choice)
        if prior!=-1:
            rows.append((probability,historical_probability,int(discovered)))
        last_action=choice
        last_discovery=int(discovered)
        last_available=int(world.memory[choice]==1)
    return rows

def compare_policies(timeline,model):
    result={}
    for name in ARMS:
        world=FrozenWorld(timeline)
        h=np.zeros(HIDDEN)
        last_action=None
        last_discovery=last_available=0
        discoveries=0
        counts=[0]*SOURCES
        for _ in timeline["states"]:
            if name=="scripted":
                choice=scripted(world)
            else:
                scores,h,_=model.step(
                    history_input(world,last_action,last_discovery,last_available),h)
                choice=forecast_policy(world,[sigmoid_scalar(s) for s in scores])
            counts[choice]+=1
            _,found=world.inspect(choice)
            discoveries+=int(found)
            last_action=choice
            last_discovery=int(found)
            last_available=int(world.memory[choice]==1)
        result[name]={
            "direct_discoveries":discoveries,
            "minimum_source_visits":min(counts)}
    return result

def reliability(rows):
    if not rows:
        raise ValueError("no directly witnessed test labels")
    brier=statistics.mean((p-y)**2 for p,_,y in rows)
    history=statistics.mean((q-y)**2 for _,q,y in rows)
    # Calibration bins are descriptive and only use directly observed probes.
    bins=[]
    for k in range(5):
        group=[(p,y) for p,_,y in rows if
               (k/5<=p<(k+1)/5 if k<4 else k/5<=p<=1)]
        bins.append({
            "probability_bin":k,
            "count":len(group),
            "mean_confidence":None if not group else round(
                statistics.mean(p for p,_ in group),6),
            "observed_change_fraction":None if not group else round(
                statistics.mean(y for _,y in group),6)})
    return {"evaluated_reinspection_labels":len(rows),
            "gru_brier":round(brier,6),
            "observed_history_baseline_brier":round(history,6),
            "calibration_bins":bins}

def benchmark(seeds=(11,17,23),episodes=180,heldout=24):
    if (not seeds or len(set(seeds))!=len(seeds)
        or any(type(x)!=int or x<0 for x in seeds)
        or type(episodes)!=int or episodes<1 or type(heldout)!=int or heldout<1):
        raise ValueError("invalid forecast study")
    cases=[]
    for seed in seeds:
        model,training_labels=train(seed+101,episodes)
        for rid,regime in enumerate(HELDOUT_REGIMES):
            for rate in RATES:
                samples=[]
                metrics={name:[] for name in ARMS}
                manifests=[]
                for e in range(heldout):
                    world_seed=SEED_OFFSET+seed*100000+rid*10000+rate*1000+e
                    trajectory=make_timeline(world_seed,regime,rate)
                    manifests.append(trajectory["sha256"])
                    samples.extend(probe_forecasts(trajectory,model,world_seed))
                    policy=compare_policies(trajectory,model)
                    for name in ARMS:
                        metrics[name].append(policy[name]["direct_discoveries"])
                assessment=reliability(samples)
                cases.append({
                    "training_seed":seed,"regime":regime,
                    "world_updates_per_inspection":rate,
                    "heldout_episodes":heldout,
                    "training_direct_reinspection_labels":training_labels,
                    "shared_trajectory_sha256":hashlib.sha256(
                        canonical(manifests).encode()).hexdigest(),
                    "forecast":assessment,
                    "mean_direct_discoveries":{
                        arm:round(statistics.mean(metrics[arm]),6) for arm in ARMS},
                    "forecast_policy_minus_scripted":round(statistics.mean(
                        a-b for a,b in zip(metrics["forecast_gated"],metrics["scripted"])),6)})
    output={
        "schema":SCHEMA,"origin":"SIMULATED_ONLY",
        "seeds":list(seeds),"training_episodes_per_seed":episodes,
        "heldout_episodes_per_cell":heldout,
        "forecast_target":"CHANGE_SINCE_LAST_DIRECT_INSPECTION",
        "first_inspections_masked_from_training_and_forecast_metrics":True,
        "training_probe_policy":"SCRIPTED_WITH_EXOGENOUS_RANDOM_EXPLORATION",
        "forecast_evaluation_policy":"SCRIPTED_WITH_EXOGENOUS_RANDOM_EXPLORATION",
        "forecast_policy":"MINIMUM_TWO_VISITS_THEN_HIGHEST_PREDICTED_CHANGE",
        "forecast_head":"SIGMOID_BERNOULLI",
        "forecast_loss":"SELECTED_SOURCE_BINARY_CROSS_ENTROPY",
        "recurrent_gradient":"EIGHT_STEP_TRUNCATED_BPTT",
        "all_policy_evaluations_use_frozen_timelines":True,
        "unselected_rewards_or_labels_used":False,
        "true_resource_volatility_available_to_model":False,
        "model_deployed_in_minecraft":False,
        "minecraft_model_promotion_authorized":False,
        "statistical_significance_claimed":False,
        "cases":cases}
    output["sha256"]=hashlib.sha256(canonical(output).encode()).hexdigest()
    return output

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--seeds",type=int,nargs="+",default=[11,17,23])
    cli.add_argument("--episodes",type=int,default=180)
    cli.add_argument("--heldout",type=int,default=24)
    cli.add_argument("--output",type=Path,default=Path("observed-change-forecast.json"))
    a=cli.parse_args()
    report=benchmark(tuple(a.seeds),a.episodes,a.heldout)
    a.output.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
    print("OBSERVED_CHANGE_FORECAST cases="+str(len(report["cases"]))+
          " forecast_and_policy_evaluated_separately=true promotion=false")

if __name__=="__main__":
    main()
