#!/usr/bin/env python3
"""Synthetic tensor reporter contract checks, not Minecraft evidence."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("report_observation_v2.py")
spec=importlib.util.spec_from_file_location("report_observation_v2",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def sample():
    lines=[]
    for stage,onehot in m.EXPECTED.items():
        tensor=[1.,0.,0.,0.,0.,*onehot,0.,0.]
        lines.append(f"REAL_OBSERVATION_V2 stage={stage} "
                     "schema=hearthbound.mill-observation.v2 tensor="
                     +",".join(str(v) for v in tensor))
    return "\n".join(lines)

def main():
    base=sample()
    record=m.analyze(base)
    assert record["width"]==10 and not record["training_performed"]
    bad=[
        base.replace("stage=empty","stage=missing",1),
        base.replace("schema=hearthbound.mill-observation.v2","schema=old",1),
        base.replace("tensor=1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0",
                     "tensor=1.0,0.0,0.0",1),
        base.replace("stage=available","stage=empty",1),
        base+"\n"+base.splitlines()[0],
        "\n".join(base.splitlines()[:2]),
        base.replace("stage=unknown","stage=available",1),
        base.replace("tensor=1.0","tensor=nan",1),
    ]
    for text in bad:
        try:m.analyze(text)
        except ValueError:pass
        else:raise AssertionError("Bad Minecraft tensor evidence accepted")
    print("PASS 9 versioned observation tensor report checks")
if __name__=="__main__":
    main()
