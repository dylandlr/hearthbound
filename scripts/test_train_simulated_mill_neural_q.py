#!/usr/bin/env python3
"""Unit and contract checks. This program evaluates a simulator, NOT Minecraft."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("train_simulated_mill_neural_q.py")
spec=importlib.util.spec_from_file_location("mill_neural_q",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    # Fully reproducible observations and environment transitions.
    for seed in range(24):
        first=m.World(seed)
        second=m.World(seed)
        assert first.state()==second.state()
        for action in ("INSPECT_SOURCE","WAIT_FOR_SUPPLY","INSPECT_SOURCE"):
            x=first.step(action)
            y=second.step(action)
            assert x==y
            assert len(x[0])==10
            assert sum(x[0][5:8])==1.
    known=m.World(40)
    known.supply=False
    known.step("INSPECT_SOURCE")
    assert known.state()[6]==1.
    known.step("WAIT_FOR_SUPPLY")
    known.step("WAIT_FOR_SUPPLY")
    # At >100 ticks known states must not remain asserted.
    known.supply=False
    known.known="EMPTY"
    known.age=101
    assert known.state()[5]==1. and known.state()[9]==1.
    # A request made without confirming availability must not earn a reward.
    denied=m.World(2)
    denied.supply=True
    _,reward,done,info=denied.step("REQUEST_WHEAT_HAUL")
    assert info["invalid_request"] and not info["success"]
    assert info["personal"]==0. and info["colony"]<0.
    # Reference can actually perform a successful one-shot task.
    available=m.World(3)
    available.supply=True
    available.step("INSPECT_SOURCE")
    _,_,done,info=available.step("REQUEST_WHEAT_HAUL")
    assert done and info["success"] and info["personal"]==1.
    q=m.NeuralQ(5)
    x=(1.,0.,0.,0.,0.,1.,0.,0.,0.,0.)
    initial=q.values(x)[2][1]
    q.train_one(x,1,initial+2.,lr=.01)
    assert q.values(x)[2][1]>initial
    report=m.benchmark(seed=13,episodes=80,heldout=20)
    assert report["training_data_origin"]=="SIMULATED_ONLY"
    assert report["minecraft_learning_claimed"] is False
    assert report["gradient_updates"]>0
    assert set(report["evaluation"])=={"neural_q","scripted_reference","untrained_network"}
    assert all(0<=row["success_rate"]<=1 for row in report["evaluation"].values())
    assert report==m.benchmark(seed=13,episodes=80,heldout=20)
    print("PASS simulated neural Q environment, gradient, reproducibility and provenance checks")

if __name__=="__main__":main()
