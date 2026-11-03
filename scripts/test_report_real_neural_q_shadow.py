#!/usr/bin/env python3
"""Synthetic fixtures exercise strict shadow-result audit, not real gameplay."""
import importlib.util
from pathlib import Path

path=Path(__file__).with_name("report_real_neural_q_shadow.py")
spec=importlib.util.spec_from_file_location("shadow_report",path)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
CHECKSUM="a"*64

def receipt(arm,stage,action=None):
    expected=m.EXPECTED[stage]
    action=action or expected
    q=[0.1,0.2,0.3]
    q[m.ACTIONS.index(action)]=0.8
    return (f"NEURAL_Q_REAL_SHADOW arm={arm} stage={stage} neural={action}"
            f" reference={expected} q="+",".join(str(x) for x in q)
            +f" checkpoint={CHECKSUM} simulator_trained=true read_only=true dispatch=false")

def fixture():
    return "\n".join(receipt(arm,stage) for arm in ("SCRIPTED","TRAINED_MLP")
                     for stage in m.EXPECTED)

def main():
    valid=fixture()
    report=m.analyze(valid)
    assert report["matches_per_arm"]=={"SCRIPTED":3,"TRAINED_MLP":3}
    assert report["game_actions_authorized"] is False
    cases=[
        valid.replace("dispatch=false","dispatch=true",1),
        valid.replace("read_only=true","read_only=false",1),
        valid.replace("simulator_trained=true","simulator_trained=false",1),
        valid.replace("reference=INSPECT_SOURCE","reference=WAIT_FOR_SUPPLY",1),
        valid.replace("checkpoint="+CHECKSUM,"checkpoint="+"b"*64,1),
        valid.replace("neural=INSPECT_SOURCE","neural=REQUEST_WHEAT_HAUL",1),
        valid+"\n"+valid.splitlines()[0],
        "\n".join(valid.splitlines()[:-1]),
        valid.replace("stage=available","stage=empty",1),
        valid.replace("q=0.1,0.2,0.8","q=nan,0.2,0.8",1),
    ]
    for bad in cases:
        try:m.analyze(bad)
        except ValueError:pass
        else:raise AssertionError("Invalid neural shadow evidence accepted")
    print("PASS 11 read-only real-neural-shadow evidence contract checks")

if __name__=="__main__":
    main()
