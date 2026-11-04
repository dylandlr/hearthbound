#!/usr/bin/env python3
"""Tests that prevent privileged simulator knowledge from entering attention."""
import evaluate_causal_attention_history as a
import train_simulated_attention_mlp as base

def assert_causal_observations():
    world=a.HistoricalWorld(313)
    assert len(world.features())==base.WIDTH
    assert world.features()[3::4]==[.5]*base.SOURCES
    before=world.features()
    world.truth=[1-v for v in world.truth]
    world.volatility=[.99]*base.SOURCES
    assert world.features()==before, "hidden truth or true volatility leaked"
    # A citizen cannot learn an unwatched source by observing source 0.
    observed=world.truth[0]
    world.inspect(0)
    assert world.last_observation[0]==observed
    assert world.observed_count==[1,0,0,0]
    assert world.features()[7::4]==[.5]*3
    previous=world.features()
    world.truth[1]=1-world.truth[1]
    world.volatility[1]=.0001
    assert world.features()==previous, "unseen source influenced model"
    # A later direct observation updates only observed source's history.
    world.truth[0]=1-world.last_observation[0]
    world.inspect(0)
    assert world.observed_changes==[1,0,0,0]
    assert world.features()[3]==1.0
    assert world.features()[7::4]==[.5]*3

def assert_independent_training():
    result=a.benchmark((3,5),train_episodes=12,eval_episodes=8,bootstrap_replicates=20)
    replay=a.benchmark((3,5),train_episodes=12,eval_episodes=8,bootstrap_replicates=20)
    assert result==replay
    assert result["origin"]=="SIMULATED_ONLY"
    assert result["privileged_volatility_feature"] is False
    assert result["true_source_availability_visible_to_policy"] is False
    assert result["minecraft_policy_deployed"] is False
    assert result["citizen_actions_authorized"] is False
    assert len(result["results"])==8
    for row in result["results"]:
        d=row["paired_discovery_difference"]
        assert d["n_paired_episodes"]==8
        assert d["bootstrap_95_ci"][0]<=d["bootstrap_95_ci"][1]
        assert -32<=d["mean"]<=32
    for kwargs in ({"train_seeds":(1,1)},{"train_seeds":()},
                   {"train_episodes":0},{"eval_episodes":0},
                   {"bootstrap_replicates":4}):
        try: a.benchmark(**kwargs)
        except ValueError: pass
        else: raise AssertionError("invalid evaluation allowed "+str(kwargs))

if __name__=="__main__":
    assert_causal_observations()
    assert_independent_training()
    print("CAUSAL_ATTENTION_HISTORY_TESTS_PASS")
