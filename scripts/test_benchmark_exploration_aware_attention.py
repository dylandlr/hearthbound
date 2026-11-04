#!/usr/bin/env python3
"""Explore/revisit incentive and no-private-information regression contracts."""
import math
from benchmark_exploration_aware_attention import (
    train_exploration, one_episode, benchmark, ARM_NAMES)
from benchmark_rapid_attention_curriculum import RapidWorld

def denied(call):
    try:call()
    except ValueError:return
    raise AssertionError("unsafe exploration training request accepted")

def main():
    # An unobserved synthetic source remains unknown to the policy even when
    # its hidden simulator state has changed repeatedly.
    world=RapidWorld(197,"unequal_volatility",4)
    before=world.features()
    assert len(before)==16
    world.inspect(0)
    after=world.features()
    assert all(after[i*4]==1 for i in (1,2,3))
    assert all(after[i*4+1]==0 for i in (1,2,3))
    assert after[0]==0
    model=train_exploration(7,8)
    assert len(model.forward(world.features())[2])==4
    denied(lambda:train_exploration(7,8,float("nan"),.1))
    denied(lambda:train_exploration(7,8,-.1,.1))
    denied(lambda:train_exploration(7,8,.1,1.))
    denied(lambda:train_exploration(7,0))
    # Test deterministic, fully held-out comparison with per-seed output.
    result=benchmark((3,5,7),12,3)
    assert result==benchmark((3,5,7),12,3)
    assert len(result["cases"])==3*4*3
    assert result["training_seeds"]==[3,5,7]
    assert not result["hidden_truth_visible_to_policy"]
    assert not result["true_volatility_visible_to_policy"]
    assert result["only_selected_source_rewards_available_to_training"]
    assert not result["real_minecraft_journals_used_for_training"]
    assert not result["model_promotion_authorized"]
    assert not result["minecraft_model_deployed"]
    assert not result["causal_superiority_claimed"]
    for case in result["cases"]:
        assert case["heldout_episodes"]==3
        assert set(case["summaries"])=={"scripted",*ARM_NAMES}
        assert set(case["differences"])==set(ARM_NAMES)
        for name in ARM_NAMES:
            d=case["differences"][name]
            assert (d["episodes_better_than_scripted"]
                    +d["episodes_worse_than_scripted"]
                    +d["episodes_tied_with_scripted"])==3
            for metric in case["summaries"][name].values():
                assert math.isfinite(metric)
    denied(lambda:benchmark((3,3,7),12,3))
    denied(lambda:benchmark((3,5,7),0,3))
    denied(lambda:benchmark((3,5,7),12,0))
    print("EXPLORATION_AWARE_ATTENTION_SIMULATION_CONTRACT_PASS")

if __name__=="__main__":
    main()
