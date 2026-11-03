#!/usr/bin/env python3
"""Synthetic-only audit fixtures for context parser. Not Minecraft evidence."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("report_mill_context_coverage.py")
s=importlib.util.spec_from_file_location("coverage",p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
def row(arm,state):
    return (f"NEURAL_Q_MILL_CONTEXT arm={arm} stage={state} "
            f"reference={m.STATES[state]} gate=ABSTAIN neural_argmax=1 "
            f"checkpoint={'a'*64} observation=REAL_MINECRAFT_REPLAY "
            "training=SIMULATED_ONLY read_only=true dispatch=false")
def main():
    good="\n".join(row(a,s) for a in ("SCRIPTED","TRAINED_MLP") for s in m.STATES)
    result=m.parse(good)
    assert result["gameplay_action_authorized"] is False
    assert result["distinct_measured_contexts"]==2
    invalid=[
        good.replace("gate=ABSTAIN","gate=REQUEST_WHEAT_HAUL",1),
        good.replace("dispatch=false","dispatch=true",1),
        good.replace("read_only=true","read_only=false",1),
        good.replace("training=SIMULATED_ONLY","training=MINECRAFT",1),
        good.replace("reference=COLLECT_OUTPUT","reference=WAIT_FOR_SUPPLY",1),
        good.replace("checkpoint="+"a"*64,"checkpoint="+"b"*64,1),
        good+"\n"+good.splitlines()[0],
        "\n".join(good.splitlines()[:-1]),
    ]
    for bad in invalid:
        try:m.parse(bad)
        except ValueError:pass
        else:raise AssertionError("Accepted invalid safety receipt")
    print("PASS 9 real-mill-context evidence safety contract checks")
if __name__=="__main__":main()
