#!/usr/bin/env python3
"""Deterministic simulated resource-seeking / job-switch contract checks."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("train_resource_task_switch.py")
spec=importlib.util.spec_from_file_location("resource_task_switch",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    # Source availability is hidden until local inspection.
    world=m.Colony(17,"primary_empty")
    assert world.vector()[5]==1 and world.vector()[10]==1
    assert world.supply=={"primary":0,"alternate":1}
    assert not m.action_mask(world.vector())[3]
    _,r,_,info=world.step(0)
    assert info["event"]=="INSPECTED_PRIMARY" and r<0
    assert world.vector()[6]==1 and not m.action_mask(world.vector())[2]
    _,_,_,info=world.step(1)
    assert info["event"]=="INSPECTED_ALTERNATE"
    assert world.vector()[12]==1 and m.action_mask(world.vector())[3]
    _,reward,done,info=world.step(3)
    assert done and info["flour_success"] and reward>1
    assert world.supply["alternate"]==0
    assert not world.other_done
    # The alternative occupation is a real simulated task transition, not
    # a free progress indicator. Completing it cannot fabricate flour.
    other=m.Colony(19,"both_empty")
    other.other_available=True
    _,reward,done,info=other.step(4)
    assert info["event"]=="OTHER_TASK_COMPLETE"
    assert reward>0 and not done and other.other_done and not other.flour_done
    _,reward,_,info=other.step(4)
    assert info["invalid"] and reward<0 and other.invalid_count==1
    # Stale known stock is treated as UNKNOWN and hauling is masked out.
    old=m.Colony(21,"primary_empty")
    old.knowledge["primary"]="AVAILABLE"
    old.observed_age["primary"]=4
    assert old.vector()[5]==1 and old.vector()[9]==1
    assert not m.action_mask(old.vector())[2]
    assert m.action_mask(old.vector())[0]
    # Reproducibility of environmental transition and both policies.
    for scenario in ("standard","primary_empty","both_empty","alternate_empty",
                     "no_secondary_job","supply_shift"):
        a=m.Colony(77,scenario)
        b=m.Colony(77,scenario)
        for _ in range(8):
            if a.finished:break
            idx=m.scripted(a.vector())
            assert idx==m.scripted(b.vector())
            assert a.step(idx)==b.step(idx)
    # Separate v1 (15-feature) contract cannot be silently fed to old v2 MLP.
    assert m.N==15 and m.SCHEMA!="hearthbound.mill-observation.v2"
    for scenario in ("primary_empty","both_empty"):
        stats=m.evaluate(m.scripted,60000000,scenario,12)
        assert stats["invalid_requests"]==0
        assert stats["episodes"]==12
        assert stats["flour_success"]+stats["timeouts"]==12
    result=m.benchmark(train_seeds=(11,13),episodes=20,eval_count=6)
    assert result==m.benchmark(train_seeds=(11,13),episodes=20,eval_count=6)
    assert result["minecraft_worlds"]==0
    assert result["minecraft_deployment_authorized"] is False
    assert result["training_origin"]==result["evaluation_origin"]=="SIMULATED_ONLY"
    assert len(result["results"])==2
    for row in result["results"]:
        assert row["weights_frozen"] and row["gradient_updates"]>0
        assert len(row["model_sha256"])==64
        assert len(row["scenarios"])==6
        for evidence in row["scenarios"].values():
            assert set(evidence)=={"heldout_seed_start","neural_q","scripted","untrained"}
            for policy in ("neural_q","scripted","untrained"):
                stats=evidence[policy]
                assert stats["episodes"]==6
                assert stats["flour_success"]+stats["timeouts"]==6
                assert stats["invalid_requests"]==0
    print("PASS resource search, alternate haul, occupation switch, masking, reproducibility and provenance")
if __name__=="__main__":main()
