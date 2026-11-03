#!/usr/bin/env python3
"""Test frozen reward ablations on simulator-only episodes."""
import importlib.util
from pathlib import Path

p=Path(__file__).with_name("ablate_resource_task_rewards.py")
spec=importlib.util.spec_from_file_location("reward_ablation",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    seed,episodes=11,35
    # Exact original-policy reproduction is an acceptance gate, not a guess.
    old,old_updates=m.base.train(seed,episodes)
    reproduced,updates=m.train("original",seed,episodes)
    assert old_updates==updates
    assert m.base.model_digest(old)==m.base.model_digest(reproduced)
    assert old.values(m.base.Colony(1).vector())==reproduced.values(m.base.Colony(1).vector())

    # Controlled transition/reward differential:
    for mode in m.MODES:
        first=m.AblationColony(19,"primary_empty",mode)
        second=m.base.Colony(19,"primary_empty")
        a=first.step(1)
        b=second.step(1)
        assert a[0]==b[0] and a[2]==b[2]
        assert a[3]["event"]==b[3]["event"]
        assert a[3]["unmodified_colony_reward"]==b[3]["colony_reward"]
        assert a[3]["unmodified_personal_reward"]==b[3]["personal_reward"]
    # Secondary rewards change only the training TD target.
    original=m.AblationColony(5,"both_empty","original")
    discounted=m.AblationColony(5,"both_empty","secondary_discount")
    original.other_available=discounted.other_available=True
    o=original.step(4)
    d=discounted.step(4)
    assert o[3]["event"]==d[3]["event"]=="OTHER_TASK_COMPLETE"
    assert abs(d[1]-(o[1]-.5))<1e-8
    assert o[3]["colony_reward"]==d[3]["colony_reward"]
    assert o[3]["personal_reward"]==d[3]["personal_reward"]
    # Primary goal training bonus is distinct from observed gameplay reward.
    original=m.AblationColony(2,"primary_empty","original")
    bonus=m.AblationColony(2,"primary_empty","goal_bonus")
    for world in (original,bonus):
        world.step(1)
    plain=original.step(3)
    boosted=bonus.step(3)
    assert plain[3]["flour_success"] and boosted[3]["flour_success"]
    assert abs(boosted[1]-plain[1]-1.)<1e-8
    assert plain[3]["colony_reward"]==boosted[3]["colony_reward"]
    # Potential-based shaping zero at terminal, nonterminal shaping telescopes.
    phi=m.potential((1,0,0,0,0,0,0,1,0,0,0,0,1,1,0))
    assert abs(phi-.30)<1e-9
    assert m.potential((1,0,0,0,0,1,0,0,0,0,1,0,0,0,0))==0.
    # Heldout evaluation records are identical in structure and reward scale.
    record=m.benchmark(training_seeds=(11,),train_episodes=30,heldout=6)
    assert record==m.benchmark(training_seeds=(11,),train_episodes=30,heldout=6)
    assert record["minecraft_worlds"]==0
    assert record["evaluation_reward_contract"]=="UNMODIFIED_V0_10_1"
    assert record["world_origin"]=="SIMULATED_ONLY"
    assert record["neural_execution_authorized"] is False
    assert set(record["modes"])==set(m.MODES)
    for row in record["results"]:
        assert len(row["scenarios"])==6
        for mode in m.MODES:
            assert row["models"][mode]["frozen_after_training"]
            assert len(row["models"][mode]["sha256"])==64
        for scenario,case in row["scenarios"].items():
            assert len(case["original"]["per_episode"])==6
            for mode in m.MODES:
                stats=case[mode]
                assert stats["flour_success"]+stats["timeouts"]==6
                assert stats["episodes"]==6
                assert stats["invalid_requests"]==0
                assert set(stats["action_counts"])==set(m.base.ACTIONS)
                assert [e["episode_seed"] for e in stats["per_episode"]]==[
                    case["heldout_seed_start"]+i for i in range(6)]
    print("PASS original model exact reproduction, reward isolation, frozen model, heldout matching and provenance")

if __name__=="__main__":
    main()
