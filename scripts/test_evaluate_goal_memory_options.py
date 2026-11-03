#!/usr/bin/env python3
"""Simulator-only option-memory tests, including persistent task resumption."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("evaluate_goal_memory_options.py")
spec=importlib.util.spec_from_file_location("goal_memory",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    model=m.base.QNetwork(9)
    # Explicit goal continuity: secondary task success returns to prior goal.
    mem=m.GoalMemory()
    x=(1.,0.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,1.,0.)
    assert m.choose(mem,x,model,step=4)==4
    assert mem.primary_goal=="PRODUCE_FLOUR" and mem.option=="SECONDARY_ONCE"
    mem.observe("OTHER_TASK_COMPLETE",step=5)
    assert mem.secondary_completed and mem.returned_to_primary
    assert mem.option=="SEEK_WHEAT"
    assert m.choose(mem,x,model,step=6)!=4
    # Work is not "completed" until actual simulated event is emitted.
    other=m.GoalMemory()
    other.transition("SECONDARY_ONCE",2)
    other.observe("WAITED",3)
    assert not other.secondary_completed and not other.returned_to_primary
    # The new scheduler cannot request hauling from hidden/empty source.
    for state in (
        (1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.,0.),
        (1.,0.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,0.,0.),
        (1.,0.,0.,0.,0.,1.,0.,0.,0.,1.,0.,1.,0.,0.,0.),
    ):
        selected=m.choose(m.GoalMemory(),state,model,0)
        assert m.base.action_mask(state)[selected]
        assert selected not in (2,3)
    # Read-only goal memory does not use hidden stock.
    a=m.base.Colony(17,"primary_empty")
    b=m.base.Colony(19,"standard")
    assert m.choose(m.GoalMemory(),a.vector(),model,0)==m.choose(
        m.GoalMemory(),b.vector(),model,0)
    for scenario in m.EVAL_SCENARIOS:
        world=m.rollout(model,123456,scenario,"hierarchical_memory",trace=True)
        assert world["invalid"]==0
        assert len(world["events"])==world["steps"]
        assert all(row["primary_goal"]=="PRODUCE_FLOUR" for row in world["events"])
        if world["secondary_then_resumed"]:
            assert any(t["from"]=="SECONDARY_ONCE" and t["to"]=="SEEK_WHEAT"
                       for t in world["option_transitions"])
    # The neural baseline must remain exactly the v0.10.2 goal-bonus result.
    learned,_=m.rewards.train("goal_bonus",11,20)
    original=m.rewards.evaluate(learned,"primary_empty",700110000,6)
    direct=m.aggregate([m.rollout(learned,700110000+i,"primary_empty",
                                  "neural_goal_bonus") for i in range(6)])
    assert direct["flour_success"]==original["flour_success"]
    assert direct["secondary_job_completion"]==original["other_job_completions"]
    assert direct["invalid_requests"]==original["invalid_requests"]
    assert direct["colony_reward_per_episode"]==original["colony_reward_per_episode"]
    record=m.benchmark(seeds=(11,),training_episodes=20,heldout=5)
    assert record==m.benchmark(seeds=(11,),training_episodes=20,heldout=5)
    assert record["new_neural_weights_trained"] is False
    assert record["recurrent_network_trained"] is False
    assert record["minecraft_worlds"]==0
    assert record["minecraft_task_dispatch_authorized"] is False
    for case in record["results"][0]["scenarios"].values():
        for policy in ("neural_goal_bonus","hierarchical_memory","scripted"):
            stats=case[policy]
            assert stats["episodes"]==5
            assert stats["flour_success"]<=5
            assert stats["invalid_requests"]==0
    print("PASS 24 goal-option resumption, source masking, baseline parity and provenance contract groups")

if __name__=="__main__":main()
