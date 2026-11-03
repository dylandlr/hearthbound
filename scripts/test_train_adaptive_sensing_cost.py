#!/usr/bin/env python3
"""Reproducibility, no hard quota, training cost and provenance checks."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("train_adaptive_sensing_cost.py")
s=importlib.util.spec_from_file_location("adaptive_sensing_cost",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def main():
    assert m.COSTS=={"free":0.,"low":.04,"medium":.12}
    assert all(x["delay"] not in (5,6,7) for x in m.TRAIN_PROFILES)
    low=m.base.QNetwork(4)
    for cost in m.COSTS.values():
        network,updates=m.train(11,low,25,cost)
        again,other=m.train(11,low,25,cost)
        assert updates>0 and updates==other
        assert m.age.digest(network)==m.age.digest(again)
    try:m.train(11,low,5,-10)
    except ValueError:pass
    else:raise AssertionError("Unregistered reward accepted")
    report=m.compare(seeds=(11,),low_episodes=15,train_episodes=20,
                     legacy_episodes=20,heldout=2)
    assert report==m.compare(seeds=(11,),low_episodes=15,train_episodes=20,
                            legacy_episodes=20,heldout=2)
    assert report["hard_refresh_budget"] is False
    assert report["minecraft_worlds"]==0
    assert report["minecraft_task_authorized"] is False
    for profile in report["results"][0]["results"].values():
        for scene in profile.values():
            for policy in (*m.COSTS,"legacy"):
                row=scene[policy]
                assert row["episodes"]==2
                assert row["executed_invalid_requests"]==0
                assert 0<=row["unintervened_valid_proposal_rate"]<=1
    print("PASS soft-cost neural training, fault distributions, reproducibility, source preflight, and simulator provenance")
if __name__=="__main__":main()
