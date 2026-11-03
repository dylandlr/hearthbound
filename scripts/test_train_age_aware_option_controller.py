#!/usr/bin/env python3
"""Age-aware policy contracts; all dynamics and rewards are simulated."""
import importlib.util
from pathlib import Path

p=Path(__file__).with_name("train_age_aware_option_controller.py")
spec=importlib.util.spec_from_file_location("age_aware",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def check():
    # A refresh is a genuine simulated WAIT tick, not a free inventory read.
    profile={"horizon":12,"delay":4,"interrupt_every":0}
    w=m.DelayedWorld(17,"primary_empty",profile)
    low=m.base.QNetwork(3)
    first,age=w.sense()
    assert age==0 and len(w.samples)==1
    assert w.sense()==(first,0) and len(w.samples)==1
    for _ in range(3):
        obs,age=w.sense()
        w.act(2,low,obs,age)
    stale,age=w.sense()
    assert age==3 and len(w.samples)==4
    # Refresh advances one world tick, but only updates the NEXT observation.
    before=w.world.steps
    reward,done,info=w.act(3,low,stale,age)
    assert w.world.steps==before+1
    fresh,age=w.sense()
    assert age==0 and fresh==w.world.vector()
    assert w.refreshes==1
    assert w.sense()==(fresh,0)
    assert len(w.samples)==4  # forcing refresh does not duplicate transport packets
    # The sensor does not expose hidden inventory: no check of world.supply.
    encoded=w.memory.encode(fresh,age)
    assert len(encoded)==21 and encoded[-1]==0.
    # A stale proposal cannot cause illegal source transfer. The safety
    # supervisor may reject and substitute WAIT, never a hidden haul.
    dangerous=m.DelayedWorld(22,"both_empty",profile)
    low=m.base.QNetwork(8)
    old=dangerous.sense()[0]
    for _ in range(3):
        seen,age=dangerous.sense()
        dangerous.act(2,low,seen,age)
    seen,age=dangerous.sense()
    assert age==3
    assert dangerous.world.invalid_count==0
    # Mask denies hallucinated actions in the observed state too.
    assert not m.option_mask((1.,0.,0.,0.,0.,0.,1.,0.,0.,0.,
                              0.,1.,0.,0.,0.))[0]
    model=m.Network(12)
    state=w.memory.encode(fresh,0)
    q_before=model.values(state)[2][3]
    model.update(state,3,q_before+1.)
    assert model.values(state)[2][3]>q_before
    assert len(m.digest(model))==64
    # A 4th option must be available even when other work and seeking are not.
    unavailable=(1.,0.,0.,0.,0.,0.,1.,0.,0.,0.,
                 0.,1.,0.,0.,0.)
    assert m.option_mask(unavailable)==(False,False,True,True)
    # Detect sensor timestamp model mismatch rather than silently granting freshness.
    try:w.memory.encode(fresh,-1)
    except ValueError:pass
    else:raise AssertionError("Negative observation age accepted")
    # Run one small matched evaluation, then repeat the entire experiment
    # to catch nondeterminism and seed leakage.
    report=m.benchmark(seeds=(11,),low_episodes=18,
                       old_episodes=22,age_episodes=25,heldout=3)
    again=m.benchmark(seeds=(11,),low_episodes=18,
                      old_episodes=22,age_episodes=25,heldout=3)
    assert report==again
    assert report["minecraft_worlds"]==0
    assert report["minecraft_execution_authorized"] is False
    assert report["results"][0]["models_frozen"]
    assert report["results"][0]["age_updates"]>0
    for scenes in report["results"][0]["profiles"].values():
        for cell in scenes.values():
            assert cell["age_aware"]["episodes"]==3
            assert cell["frozen_legacy"]["episodes"]==3
            assert cell["age_aware"]["invalid_requests"]==0
            assert cell["age_aware"]["safety_rejections"]>=0
            assert len(cell["trace"])>0
    print("PASS age-aware refresh timing, stale safety, TD updates, deterministic baselines and provenance")

if __name__=="__main__":
    check()
