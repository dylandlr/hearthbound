#!/usr/bin/env python3
"""Unseen resource stress controls, deterministic paired replay, no promotion."""
import copy
from benchmark_forecast_policy_stress import (
    make_stress_timeline,benchmark,SCHEDULES,LENGTH,ARMS)
from benchmark_frozen_attention_timelines import FrozenWorld

def refused(callback):
    try:callback()
    except ValueError:return
    raise AssertionError("invalid stress timeline accepted")

def main():
    for name in SCHEDULES:
        t=make_stress_timeline(103,name)
        assert t==make_stress_timeline(103,name)
        assert len(t["states"])==LENGTH
        assert len(t["latent_change_counts_between_decisions"])==LENGTH-1
        assert len(t["sha256"])==64
        w=FrozenWorld(t)
        assert all(w.features()[i*4]==1 for i in range(4))
        for step in range(LENGTH):
            choice=step%4
            w.inspect(choice)
        refused(lambda:w.inspect(0))
        damaged=copy.deepcopy(t)
        damaged["states"][4][0]^=1
        refused(lambda:FrozenWorld(damaged))
    depleted=make_stress_timeline(103,"permanent_depletion")["states"]
    assert all(all(depleted[t+1][s]<=depleted[t][s]
                   for t in range(LENGTH-1)) for s in range(4))
    bursty=make_stress_timeline(103,"bursty_mutations")
    assert any(v>0 for v in bursty["latent_change_counts_between_decisions"])
    long_gap=make_stress_timeline(103,"long_observation_gaps")
    assert sum(long_gap["latent_change_counts_between_decisions"])==4
    refused(lambda:make_stress_timeline(1,"invented"))
    refused(lambda:make_stress_timeline(1,"bursty_mutations",12))
    small=benchmark((3,5,7),8,2)
    assert small==benchmark((3,5,7),8,2)
    assert len(small["results"])==len(SCHEDULES)*3
    assert small["same_frozen_model_per_seed_across_all_arms"]
    assert small["same_hidden_timeline_per_episode_across_all_arms"]
    assert small["stress_schedules_used_in_training"] is False
    assert small["minecraft_model_promotion_authorized"] is False
    assert small["observation_only_selected_source"]
    for row in small["results"]:
        assert set(row["mean_direct_discoveries"])==set(ARMS)
        for arm,diffs in row["paired_discovery_differences"].items():
            assert len(diffs)==2
            assert row["mean_difference_from_scripted"][arm]==sum(diffs)/2
    refused(lambda:benchmark((3,3,7),8,2))
    refused(lambda:benchmark((3,5,7),8,0))
    print("FROZEN_FORECAST_OUT_OF_DISTRIBUTION_STRESS_CONTRACT_PASS")

if __name__=="__main__":
    main()
