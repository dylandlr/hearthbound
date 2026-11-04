#!/usr/bin/env python3
"""Deterministic safety and causal-history tests for synthetic curricula."""
from benchmark_rapid_attention_curriculum import RapidWorld,benchmark,train,evaluate

def denied(callback):
    try:callback()
    except ValueError:return
    raise AssertionError("invalid rapid-attention simulator accepted")

def main():
    world=RapidWorld(911,"unequal_volatility",4)
    assert len(world.features())==16
    before=world.features()
    assert all(before[4*i]==1. for i in range(4))
    source=0
    reward,discovered=world.inspect(source)
    assert discovered and reward==.96
    after=world.features()
    assert after[0]==0.
    # Other sources remain unobserved even when the latent simulator changes.
    assert all(after[4*i]==1. for i in range(1,4))
    assert world.latent_transitions>=0
    denied(lambda:RapidWorld(1,"in_distribution",0))
    denied(lambda:RapidWorld(1,"in_distribution",9))
    model=train(5,9,True)
    result=evaluate(model,100,"high_volatility",4,3)
    assert len(result["paired_episode_differences"])==3
    assert result["neural_mean_direct_discoveries"]>=0
    x=benchmark(7,9,3)
    assert x==benchmark(7,9,3)
    assert len(x["results"])==12
    assert x["origin"]=="SIMULATED_ONLY"
    assert x["minecraft_policy_deployed"] is False
    assert x["model_replacement_authorized"] is False
    assert x["true_volatility_input_to_policy"] is False
    assert x["unselected_truth_input_to_policy"] is False
    assert all(set(record)=={
        "regime","world_updates_per_inspection","heldout_episodes",
        "legacy_style","mixed_rapid_curriculum"} for record in x["results"])
    denied(lambda:benchmark(5,0,1))
    denied(lambda:benchmark(5,9,0))
    print("RAPID_ATTENTION_CURRICULUM_SIMULATOR_CONTRACT_PASS")

if __name__=="__main__":
    main()
