#!/usr/bin/env python3
"""Deterministic option stress contracts, including stale-action rejection."""
import importlib.util
from pathlib import Path

p=Path(__file__).with_name("evaluate_option_interruption_stress.py")
spec=importlib.util.spec_from_file_location("option_stress",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    low,_=m.rewards.train("goal_bonus",11,20)
    meta,_=m.options.train_meta(11,low,20)
    clean={"horizon":14,"delay":0,"interrupt_every":0}
    for scenario in m.SCENARIOS:
        for policy in m.POLICIES:
            new=m.replay(meta,low,7654321,scenario,policy,clean,True)
            old_policy={
                "learned_options":"learned_options",
                "engineered_memory":"engineered_memory",
                "frozen_neural":"frozen_neural",
                "scripted":"scripted",
            }[policy]
            original=m.options.rollout(meta,low,7654321,scenario,old_policy)
            assert new["flour_success"]==original["flour_success"],(scenario,policy)
            assert new["other_job"]==original["secondary_completed"],(scenario,policy)
            assert new["invalid_requests"]==original["invalid_requests"]
            assert new["colony_reward"]==original["colony_reward"]
            assert new["personal_reward"]==original["personal_reward"]
            assert len(new["trace"])==new["steps"]
    stressed={"horizon":42,"delay":4,"interrupt_every":5}
    for scenario in m.SCENARIOS:
        for policy in m.POLICIES:
            outcome=m.replay(meta,low,9753101,scenario,policy,stressed,True)
            assert outcome["invalid_requests"]==0
            assert outcome["forced_interruptions"]>=0
            assert len(outcome["trace"])==outcome["steps"]
            assert all(x["executed_action"] in m.base.ACTIONS for x in outcome["trace"])
            assert all(x["received_event"] in (
                "WAITED","DENIED_HAUL","DENIED_OTHER_JOB","FLOUR_TASK_COMPLETE",
                "OTHER_TASK_COMPLETE","INSPECTED_PRIMARY","INSPECTED_ALTERNATE",
                "EXOGENOUS_PRIMARY_RESTOCK") for x in outcome["trace"])
    # Unseen seed space, no Minecraft provenance, frozen model and repeatability.
    result=m.benchmark(seeds=(11,),low_episodes=20,meta_episodes=20,heldout=3)
    assert result==m.benchmark(seeds=(11,),low_episodes=20,meta_episodes=20,heldout=3)
    assert result["minecraft_worlds_executed"]==0
    assert result["minecraft_action_authorized"] is False
    assert result["result"][0]["frozen"]
    assert len(result["result"][0]["profiles"])==5
    for prof in result["result"][0]["profiles"].values():
        for scene in prof.values():
            for policy in m.POLICIES:
                assert scene[policy]["episodes"]==3
                assert scene[policy]["invalid_requests"]==0
                assert scene[policy]["flour_success"]<=3
    print("PASS clean-run parity, delayed sensors and events, interruption safety, frozen seeds and provenance")

if __name__=="__main__": main()
