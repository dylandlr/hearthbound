#!/usr/bin/env python3
"""Pure synthetic parser checks. These records are NOT Minecraft evidence."""
import importlib.util
from pathlib import Path

path=Path(__file__).with_name("report_live_shadow.py")
spec=importlib.util.spec_from_file_location("report_live_shadow",path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

CITIZEN="123e4567-e89b-12d3-a456-426614174000"

def line(stage,expected):
    experience=1 if stage=="citizen_experienced" else 0
    flour=0 if stage=="empty_powered" else 2
    return (f"LIVE_SHADOW_PAIR stage={stage} expected={expected} "
            f"scripted={expected} trained={expected} raw_mlp={expected} "
            f"citizen={CITIZEN} powered=true wheat=0 flour={flour} "
            f"blocked=false experience={experience} disagreement=false "
            f"masked=false read_only=true")

def fixture():
    return "\n".join(line(stage,expected) for stage,expected in module.REQUIRED.items())

def main():
    valid=fixture()
    report=module.analyze(valid)
    assert len(report["stages"])==3
    assert report["read_only"] is True
    assert report["learning_improvement_demonstrated"] is False
    cases=(
        valid.replace("trained=COLLECT_OUTPUT","trained=WAIT_FOR_PROCESSING",1),
        valid.replace("read_only=true","read_only=false",1),
        valid.replace("citizen_experienced","other_experiment"),
        valid+"\n"+valid.splitlines()[0],
        valid.replace("experience=1","experience=0"),
        valid.replace("flour=2","flour=0"),
        valid.replace("disagreement=false","disagreement=true"),
        valid.replace("masked=false","masked=true"),
        valid.replace(CITIZEN,"other-citizen",1),
        valid.replace("powered=true","powered=false",1),
        valid.splitlines()[0]+"\n"+valid.splitlines()[1],
    )
    for invalid in cases:
        try:module.analyze(invalid)
        except ValueError:pass
        else:raise AssertionError("Invalid shadow report was accepted")
    print("PASS 12 compact real-shadow report validation checks")

if __name__=="__main__":main()
