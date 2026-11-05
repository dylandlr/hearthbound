#!/usr/bin/env python3
"""Frozen forecaster, guarded decisions and matched-timeline contracts."""
import copy
import math
from benchmark_forecast_policy_gating import (
    select,episode,benchmark,ARMS,AGE_WEIGHT)
from benchmark_observed_change_forecast import train as train_forecaster
from benchmark_frozen_attention_timelines import make_timeline,FrozenWorld
from train_simulated_attention_mlp import scripted

def rejected(fn):
    try:fn()
    except ValueError:return
    raise AssertionError("invalid input accepted")

def main():
    world=FrozenWorld(make_timeline(111,"unequal_volatility",2))
    p=[.10,.30,.70,.90]
    for arm in ARMS:
        action,_=select(world,p,arm)
        assert action==scripted(world)
    rejected(lambda:select(world,[float("nan"),.1,.2,.3],"scripted"))
    rejected(lambda:select(world,[float("inf"),.1,.2,.3],"age_blend"))
    rejected(lambda:select(world,[.1,.2,.3],"greedy_forecast"))
    rejected(lambda:select(world,[.1,.2,.3,1.1],"coverage_guard"))
    rejected(lambda:select(world,p,"invented"))
    rejected(lambda:select(world,p,"scripted",streak=-1))
    world.observed_count=[3,3,3,3]
    world.observed_changes=[1,1,1,1]
    world.ages=[0,5,10,20]
    # A spread below the precommitted threshold triggers scripted fallback.
    action,active=select(world,[.45,.48,.51,.54],"coverage_guard")
    assert action==scripted(world) and not active
    # Under reliable differentiated predictions, the gate may prioritize
    # a different source, but its own observation history remains causal.
    action,_=select(world,[.9,.2,.1,.1],"coverage_guard")
    assert action==0
    action,active=select(world,[.9,.2,.1,.1],"coverage_guard",0,2)
    assert action==scripted(world) and not active
    assert math.isclose(AGE_WEIGHT,.35)
    model,n=train_forecaster(7,8)
    assert n>0
    initial={k:v.copy() for k,v in model.params.items()}
    t=make_timeline(445,"unequal_volatility",4)
    first=episode(t,model)
    assert first==episode(copy.deepcopy(t),model)
    assert set(first)==set(ARMS)
    assert all(0<=row["direct_discoveries"]<=32 for row in first.values())
    assert all(0<=row["distinct_sources"]<=4 for row in first.values())
    assert all((model.params[k]==v).all() for k,v in initial.items())
    report=benchmark((3,5,7),8,2)
    assert report==benchmark((3,5,7),8,2)
    assert len(report["cases"])==36
    assert report["same_frozen_forecaster_for_every_policy_per_seed"]
    assert report["frozen_trajectories_shared_between_policies"]
    assert report["policy_can_access_unselected_source_truth"] is False
    assert report["minecraft_model_promotion_authorized"] is False
    for case in report["cases"]:
        assert set(case["mean_direct_discoveries"])==set(ARMS)
        assert case["frozen_model_sha256"]==report[
            "model_hashes_by_training_seed"][str(case["training_seed"])]
    rejected(lambda:benchmark((3,3,7),8,2))
    rejected(lambda:benchmark((3,5,7),0,2))
    print("FROZEN_FORECAST_POLICY_CAUSAL_GATE_CONTRACT_PASS")

if __name__=="__main__":
    main()
