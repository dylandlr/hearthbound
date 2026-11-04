#!/usr/bin/env python3
"""Regressions for policy-independent hidden trajectories and privacy."""
import copy
from benchmark_frozen_attention_timelines import (
    make_timeline,FrozenWorld,replay,benchmark,HORIZON)
from benchmark_exploration_aware_attention import train_exploration
from benchmark_observed_uncertainty_objective import train_objective

def denied(callback):
    try:callback()
    except ValueError:return
    raise AssertionError("accepted invalid fixed latent state or observation")

def main():
    t=make_timeline(888,"unequal_volatility",4)
    assert t==make_timeline(888,"unequal_volatility",4)
    assert t!=make_timeline(889,"unequal_volatility",4)
    assert len(t["states"])==HORIZON
    assert len(t["latent_change_counts_between_decisions"])==HORIZON-1
    assert all(len(x)==4 for x in t["states"])
    world=FrozenWorld(t)
    x=world.features()
    assert len(x)==16 and all(x[i*4]==1 for i in range(4))
    world.inspect(0)
    y=world.features()
    assert y[0]==0 and all(y[i*4]==1 for i in (1,2,3))
    # Mutating the trajectory without resigning must be rejected.
    corrupted=copy.deepcopy(t)
    corrupted["states"][4][0]^=1
    denied(lambda:FrozenWorld(corrupted))
    denied(lambda:world.inspect(8))
    denied(lambda:make_timeline(1,"other",2))
    denied(lambda:make_timeline(1,"unequal_volatility",0))
    models={"exploration_neural":train_exploration(7,9),
            "uncertainty_neural":train_objective(8,9)}
    outcomes=replay(t,models)
    assert outcomes==replay(copy.deepcopy(t),models)
    assert all(sum(v["source_visits"])==HORIZON for v in outcomes.values())
    assert all(v["direct_discoveries"]<=HORIZON for v in outcomes.values())
    # Precomputing and holding a single timeline means every policy sees the
    # identical latent change sequence despite divergent choices.
    assert t==make_timeline(888,"unequal_volatility",4)
    a=benchmark((3,5,7),12,3)
    assert a==benchmark((3,5,7),12,3)
    assert len(a["cases"])==36
    assert a["all_arms_share_identical_latent_trajectories"] is True
    assert a["resource_timeline_visible_to_policy"] is False
    assert a["model_promotion_authorized"] is False
    assert a["real_forge_performance_claimed"] is False
    denied(lambda:benchmark((3,3,7),12,3))
    denied(lambda:benchmark((3,5,7),12,0))
    print("FROZEN_ATTENTION_TIMELINE_PRIVACY_AND_REPLAY_CONTRACT_PASS")

if __name__=="__main__":
    main()
