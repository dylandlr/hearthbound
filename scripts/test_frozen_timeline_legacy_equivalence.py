#!/usr/bin/env python3
"""Cross-engine equivalence: legacy stochastic stepping vs frozen replay.

The older RapidWorld draws all source transitions after each inspection,
independent of the selected source. This test demonstrates that it already
produced policy-independent hidden trajectories under the same initial seed.
"""
from benchmark_frozen_attention_timelines import make_timeline,FrozenWorld
from benchmark_rapid_attention_curriculum import RapidWorld

def check(seed,regime,rate,actions):
    old=RapidWorld(seed,regime,rate)
    timeline=make_timeline(seed,regime,rate,horizon=len(actions))
    new=FrozenWorld(timeline)
    assert tuple(old.truth)==tuple(timeline["states"][0])
    for step,action in enumerate(actions):
        # The same visible history must produce the same sensor feature vector
        # before each action, without exposing unselected current/future truth.
        assert old.features()==new.features(),(seed,regime,rate,step,"features")
        a=old.inspect(action)
        b=new.inspect(action)
        assert a==b,(seed,regime,rate,step,"selected_outcome")
        assert old.features()==new.features(),(seed,regime,rate,step,"postinspection_features")
        if step+1<len(actions):
            assert tuple(old.truth)==tuple(timeline["states"][step+1]),(
                seed,regime,rate,step,"hidden_truth")
    return timeline["sha256"]

def main():
    for seed in (1,101,999):
        for regime in ("in_distribution","low_volatility","unequal_volatility","high_volatility"):
            for rate in (1,2,4):
                # Deliberately contrast policies that focus a source with
                # policies that rotate all sources, on the same latent draws.
                rotating=[x%4 for x in range(32)]
                focused=[0 for _ in range(32)]
                irregular=[(x*x+3*x+seed)%4 for x in range(32)]
                digest=check(seed,regime,rate,rotating)
                assert check(seed,regime,rate,focused)==digest
                assert check(seed,regime,rate,irregular)==digest
    print("LEGACY_AND_FROZEN_WORLD_SAME_POLICY_INDEPENDENT_LATENT_TIMELINE_PASS")

if __name__=="__main__":
    main()
