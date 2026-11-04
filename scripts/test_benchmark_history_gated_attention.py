#!/usr/bin/env python3
"""History-gated MLP contract, counterfactual and reproducibility tests."""
from benchmark_history_gated_attention import benchmark,gate,evaluate_episode
from benchmark_rapid_attention_curriculum import RapidWorld
from train_simulated_attention_mlp import MLP,scripted

def refused(call):
    try:call()
    except ValueError:return
    raise AssertionError("invalid causal history accepted")

def main():
    model=MLP(8)
    world=RapidWorld(789,"unequal_volatility",4)
    decision,active=gate(world,model)
    assert decision==scripted(world) and active is False
    assert len(world.features())==16
    assert all(world.features()[i*4]==1. for i in range(4))
    world.inspect(0)
    assert all(world.features()[i*4]==1. for i in (1,2,3))
    # Even a high observed change-rate spread must not bypass the
    # minimum independent direct inspection history or neural burst cap.
    world.observed_count=[3,3,3,3]
    world.observed_changes=[2,0,0,0]
    decision,active=gate(world,model,last_neural_choices=2)
    assert decision==scripted(world) and not active
    _,active=gate(world,model,last_neural_choices=0)
    assert active
    world.observed_changes=[1,1,1,1]
    _,active=gate(world,model,last_neural_choices=0)
    assert not active
    refused(lambda:gate(world,model,-1))
    refused(lambda:benchmark((11,11,17),10,3))
    refused(lambda:benchmark((11,17,23),0,3))
    refused(lambda:benchmark((11,17,23),10,0))
    case=evaluate_episode(888,"low_volatility",2,model)
    assert set(case)=={"scripted","neural","gated"}
    assert case["scripted"]["neural_choices"]==0
    assert case["neural"]["neural_choices"]==32
    assert 0<=case["gated"]["neural_choices"]<=32
    result=benchmark((3,5,7),12,3)
    assert result==benchmark((3,5,7),12,3)
    assert len(result["cases"])==36
    assert len(result["regimes"])==4
    assert result["origin"]=="SIMULATED_ONLY"
    assert not result["minecraft_policy_deployed"]
    assert not result["model_promotion_authorized"]
    assert not result["hidden_resource_state_visible_to_policy"]
    assert not result["true_volatility_visible_to_policy"]
    assert all(0<=x["gated_mean_neural_decisions_per_episode"]<=32 for x in result["cases"])
    print("HISTORY_GATED_ATTENTION_SIMULATOR_CONTRACT_PASS")

if __name__=="__main__":
    main()
