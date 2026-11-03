#!/usr/bin/env python3
"""Safety, genuine gradient, option-history and comparator-parity tests."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("train_learned_option_controller.py")
spec=importlib.util.spec_from_file_location("learned_options",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    initial=m.OptionQ(5)
    obs=m.base.Colony(1).vector()
    memory=m.AgentHistory()
    x=memory.state(obs)
    assert len(x)==19
    before=initial.values(x)[2][1]
    initial.update(x,1,before+1)
    assert initial.values(x)[2][1]>before
    # Switching is controlled by selected option, not by hardcoded job event.
    memory.register(1,"OTHER_TASK_COMPLETE")
    assert memory.previous_option==1 and memory.just_completed_secondary
    assert memory.returned_to_primary==0
    memory.register(2,"WAITED")
    assert memory.switches==1 and memory.returned_to_primary==0
    memory.register(1,"OTHER_TASK_COMPLETE")
    memory.register(0,"INSPECTED_PRIMARY")
    assert memory.returned_to_primary==1
    # Empty chests cannot justify a haul or repeated unnecessary inspection.
    empty=(1.,0.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,1.,0.)
    assert m.mask(empty)==(False,True,True)
    known=(1.,0.,0.,0.,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.)
    assert m.mask(known)[0] is True
    assert m.execute(0,known,m.base.QNetwork(4))==2
    unknown=m.base.Colony(10).vector()
    assert m.mask(unknown)[0] is True
    assert m.execute(0,unknown,m.base.QNetwork(4)) in (0,1)
    for state in (empty,known,unknown):
        for idx in range(3):
            if m.mask(state)[idx]:
                chosen=m.execute(idx,state,m.base.QNetwork(4))
                assert m.base.action_mask(state)[chosen]
    # Reproduced feedforward and engineered controls must agree with v0.10.3.
    low,_=m.rewards.train("goal_bonus",11,25)
    meta,_=m.train_meta(11,low,25)
    for policy in ("frozen_neural","engineered_memory","scripted","learned_options"):
        result=m.rollout(meta,low,1234,"primary_empty",policy,trace=True)
        assert result["invalid_requests"]==0
        assert len(result["events"])==result["steps"]
    a=m.rollout(meta,low,1234,"primary_empty","engineered_memory")
    b=m.old.rollout(low,1234,"primary_empty","hierarchical_memory")
    assert a["flour_success"]==b["flour"]
    assert a["secondary_completed"]==b["other_job"]
    assert a["colony_reward"]==b["colony_reward"]
    report=m.benchmark(seeds=(11,),low_episodes=25,meta_episodes=25,heldout=5)
    assert report==m.benchmark(seeds=(11,),low_episodes=25,meta_episodes=25,heldout=5)
    assert report["meta_option_selection_learned"] is True
    assert report["recurrent_network_trained"] is False
    assert report["minecraft_worlds"]==0
    assert report["minecraft_execution_authorized"] is False
    assert report["results"][0]["meta_updates"]>0
    for case in report["results"][0]["scenarios"].values():
        for policy in ("learned_options","frozen_neural","engineered_memory","scripted"):
            stats=case[policy]
            assert stats["episodes"]==5
            assert stats["invalid_requests"]==0
            assert stats["flour_success"]<=5
    print("PASS learned upper-option gradient, true option switches, bounded executor, baseline parity and reproducibility")
if __name__=="__main__":main()
