#!/usr/bin/env python3
"""Fast deterministic contract checks; all worlds below are simulated."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("evaluate_neural_q_stress.py")
spec=importlib.util.spec_from_file_location("stress",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def main():
    no_restock={"restock":0.,"horizon":5,"initial_supply_probability":0.}
    world=m.StressWorld(17,no_restock)
    for i in range(4):
        observation=world.state()
        world.step(m.scripted(observation))
    assert world.supply is False
    assert world.state()[6]==1. or world.state()[5]==1.
    # Frozen gate must reject mismatched actions, all unsupported machine
    # contexts, and stale inventory, regardless of neural scores.
    for name,x in m.OOD_MACHINE_STATES.items():
        for action in range(3):
            assert m.guarded_action(x,action) is False,(name,action)
    valid_unknown=(1.,0.,0.,0.,0.,1.,0.,0.,0.,0.)
    valid_empty=(1.,0.,0.,0.,0.,0.,1.,0.,0.,0.)
    valid_available=(1.,0.,0.,0.,0.,0.,0.,1.,0.,0.)
    for idx,x in enumerate((valid_unknown,valid_empty,valid_available)):
        for action in range(3):
            assert m.guarded_action(x,action)==(idx==action)
    # No resource can arrive when restock probability is exactly zero.
    no_supply=m.evaluate(m.scripted,1234,no_restock,12)
    assert no_supply["successes"]==0
    assert no_supply["timeouts"]==12
    assert no_supply["personal_reward_per_episode"]==0
    # Explicit seed-based isolation, deterministic full baseline and
    # checkpoint immutability. Test with bounded episode counts.
    report=m.benchmark(training_seeds=(11,13),train_episodes=30,eval_episodes=8)
    again=m.benchmark(training_seeds=(11,13),train_episodes=30,eval_episodes=8)
    assert report==again
    assert report["actual_minecraft_worlds"]==0
    assert report["neural_task_execution_authorized"] is False
    assert report["minecraft_learning_demonstrated"] is False
    assert report["scenario_count"]==5
    for result in report["results"]:
        assert result["checkpoint_unchanged"]
        assert len(result["checkpoint_sha256"])==64
        for condition,values in result["ood_machine_states"].items():
            assert values["gate"]=="ABSTAIN",(condition,values)
            assert values["task_dispatched"] is False
        for scenario,row in result["scenarios"].items():
            starts={row["eval_seed_start"]+i for i in range(8)}
            assert len(starts)==8
            for policy in ("neural_q","scripted_reference","untrained_network"):
                stats=row[policy]
                assert stats["episodes"]==8
                assert stats["successes"]+stats["timeouts"]==8
                assert 0<=stats["success_rate"]<=1
                assert stats["invalid_requests"]>=0
    print("PASS multi-seed stress reproducibility, held-out OOD guards, reward and provenance contracts")

if __name__=="__main__":
    main()
