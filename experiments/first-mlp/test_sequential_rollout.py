#!/usr/bin/env python3
"""Deterministic checks of the sequential surrogate dynamics (not game tests)."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from sequential_rollout import ColonyEpisode, rollout

def test():
    a=ColonyEpisode(99)
    b=ColonyEpisode(99)
    assert a.scenario()==b.scenario()
    for action in [2,3,4,0,1,2,3]:
        a.step(action); b.step(action)
        assert a.scenario()==b.scenario()
        assert a.flour==b.flour and a.waste==b.waste
    c=ColonyEpisode(1)
    c.wheat=1; c.power=True; c.threat=0
    c.step(3)
    assert c.flour==1 and c.wheat==0
    d=ColonyEpisode(1)
    d.wheat=0; d.power=True; d.threat=0
    d.step(3)
    assert d.flour==0 and d.waste==1
    e=ColonyEpisode(1)
    e.threat=.9
    e.step(3)
    assert e.unsafe==1
    x=rollout(lambda s: 4,[100,101,102],8)
    assert x["episodes"]==3 and x["mean_flour"]==0
    print("PASS: sequential dynamics deterministic, production requires resources, unsafe decisions tracked")

if __name__=="__main__": test()
