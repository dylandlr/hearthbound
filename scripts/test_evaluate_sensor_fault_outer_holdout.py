#!/usr/bin/env python3
"""Outer-holdout contract checks: failed refresh, budget, drift, no private data."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("evaluate_sensor_fault_outer_holdout.py")
spec=importlib.util.spec_from_file_location("sensor_fault",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    assert {p["delay"] for p in m.FAULTS.values()}=={5,6,7}
    assert all(p["budget"]>0 for p in m.FAULTS.values())
    low=m.base.QNetwork(5)
    profile={"horizon":16,"delay":6,"interrupt_every":0,
             "fail_mod":1,"budget":1,"drift_every":0}
    w=m.FaultWorld(31,"primary_empty",profile)
    obs,age=w.sense()
    finished,_=w.act_faulted(3,low,obs,age,True,True)
    assert not finished
    assert w.refresh_attempts==1 and w.refresh_failures==1
    assert w.forced_current is None
    obs,age=w.sense()
    assert age>=1  # always-failed refresh can't invent a current sample
    step=w.world.steps
    w.act_faulted(3,low,obs,age,False,True)
    assert w.world.steps==step+1
    assert w.refresh_budget_denials==1
    assert w.refresh_attempts==2
    assert w.refreshes==1
    assert w.world.invalid_count==0
    # Inventory drift is a real change to hidden simulated environment,
    # not a mutation to a previously delivered sensor snapshot.
    drifting={"horizon":16,"delay":5,"interrupt_every":0,
              "fail_mod":0,"budget":2,"drift_every":2}
    world=m.FaultWorld(7,"primary_empty",drifting)
    original,age=world.sense()
    world.act_faulted(2,low,original,age,True)
    world.act_faulted(2,low,*world.sense(),True)
    assert world.inventory_drift_events==1
    assert world.world.invalid_count==0
    assert original==m.base.Colony(7,"primary_empty").vector()
    # Both policies are evaluated under the same fault schedule; no model
    # gets privileged access to current supply prior to its action proposal.
    old=m.legacy.OptionQ(3)
    new=m.age.Network(4)
    for scenario in m.SCENARIOS:
        for policy in m.POLICIES:
            result=m.replay(new,old,low,5001,scenario,drifting,policy,True)
            assert result["executed_invalid_requests"]==0
            assert result["steps"]==len(result["trace"])
            assert all(event["actual_inventory_redacted"] for event in result["trace"])
            if policy=="frozen_legacy":
                assert result["refresh_attempts"]==0
            if policy=="age_aware_budgeted":
                assert result["refresh_executed"]<=drifting["budget"]
    report=m.benchmark(seeds=(11,),low_episodes=15,old_episodes=18,
                       age_episodes=21,heldout=2)
    assert report==m.benchmark(seeds=(11,),low_episodes=15,old_episodes=18,
                               age_episodes=21,heldout=2)
    assert report["minecraft_worlds"]==0
    assert report["minecraft_task_authorized"] is False
    assert report["outer_profiles_unseen_in_training"] is True
    assert report["results"][0]["frozen_checkpoints"]
    for group in report["results"][0]["profiles"].values():
        for case in group.values():
            for policy in m.POLICIES:
                assert case[policy]["episodes"]==2
                assert case[policy]["executed_invalid_requests"]==0
                if policy=="age_aware_budgeted":
                    assert case[policy]["refresh_executed"]<=2*max(
                        p["budget"] for p in m.FAULTS.values())
    print("PASS sensor fault schedules, no free refresh, strict budgets, hidden inventory and reproducibility")

if __name__=="__main__":main()
