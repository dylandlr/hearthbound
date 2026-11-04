#!/usr/bin/env python3
"""Regression contracts for multi-seed synthetic attention robustness."""
import evaluate_simulated_attention_robustness as r
import train_simulated_attention_mlp as base

def run_tests():
    a = r.benchmark((7,13), train_episodes=20, eval_episodes=12, bootstrap_replicates=30)
    b = r.benchmark((7,13), train_episodes=20, eval_episodes=12, bootstrap_replicates=30)
    assert a == b, "multi-seed results must replay deterministically"
    assert a["origin"] == "SIMULATED_ONLY"
    assert a["citizen_actions_authorized"] is False
    assert a["minecraft_policy_deployed"] is False
    assert len(a["results"]) == 8
    assert set(a["training_seeds"]) == {7,13}
    for entry in a["results"]:
        diff = entry["paired_discovery_difference"]
        assert diff["n_paired_episodes"] == 12
        assert diff["bootstrap_replicates"] == 30
        low, high = diff["bootstrap_95_ci"]
        assert low <= high
        assert -32 <= low <= 32 and -32 <= high <= 32
    x = base.World(123).features()
    for regime in a["regimes"]:
        world = r.make_world(123,regime)
        assert len(world.features()) == base.WIDTH
        # Hidden resource truth should never appear in the observation vector.
        before = world.features()
        world.truth = [1-v for v in world.truth]
        assert world.features() == before
    assert x == r.make_world(123, "in_distribution").features()
    for kwargs in (
        {"train_seeds": (1,1)},
        {"train_seeds": ()},
        {"eval_episodes": 0},
        {"bootstrap_replicates": 4}
    ):
        try:
            r.benchmark(**kwargs)
        except ValueError:
            pass
        else:
            raise AssertionError("unsafe evaluation configuration accepted: "+str(kwargs))
    print("ATTENTION_ROBUSTNESS_CONTRACT_PASS")

if __name__=="__main__":
    run_tests()
