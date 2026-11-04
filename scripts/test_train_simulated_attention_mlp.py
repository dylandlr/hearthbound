#!/usr/bin/env python3
"""Pure-Python regression tests for the simulated attention experiment."""
import importlib.util
from pathlib import Path

path=Path(__file__).with_name("train_simulated_attention_mlp.py")
spec=importlib.util.spec_from_file_location("attention",path)
a=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)

def test_determinism():
    first=a.benchmark(seed=17,episodes=24,heldout=12)
    second=a.benchmark(seed=17,episodes=24,heldout=12)
    assert first==second, "same seed must reproduce all results"
    assert first["origin"]=="SIMULATED_ONLY"
    assert first["minecraft_policy_deployed"] is False
    assert first["citizen_actions_authorized"] is False
    assert first["observations_per_decision"]==1
    assert set(first["evaluation"])=={
        "scripted_least_recent","trained_mlp","untrained_mlp"}
    for values in first["evaluation"].values():
        assert values["episodes"]==12
        assert values["inspections_per_episode"]==32

def test_observation_mask():
    a_world=a.World(314)
    x=a_world.features()
    assert len(x)==a.WIDTH
    original_memory=a_world.memory[:]
    # Changing hidden state must not directly change any policy input.
    a_world.truth=[1-v for v in a_world.truth]
    assert a_world.features()==x
    assert a_world.memory==original_memory
    # Inspection is the only way to reveal a truth state.
    a_world.inspect(0)
    assert a_world.memory[0] in (0,1)
    assert all(v==-1 for v in a_world.memory[1:])

def test_budget_and_controls():
    model=a.MLP(0)
    world=a.World(9)
    assert len(model.forward(world.features())[2])==a.SOURCES
    for _ in range(40):
        action=a.learned(model,world)
        assert 0<=action<a.SOURCES
        before=world.step_count
        world.inspect(action)
        assert world.step_count==before+1
    for count in (0,-1):
        try: a.benchmark(episodes=count)
        except ValueError: pass
        else: raise AssertionError("invalid episode count accepted")

if __name__=="__main__":
    test_determinism()
    test_observation_mask()
    test_budget_and_controls()
    print("SIMULATED_ATTENTION_TESTS_PASS")
