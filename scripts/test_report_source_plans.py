#!/usr/bin/env python3
"""Offline parser fixtures, not verified gameplay evidence."""
import importlib.util
from pathlib import Path
p=Path(__file__).with_name("report_source_plans.py")
spec=importlib.util.spec_from_file_location("report_source_plans",p)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def fixture():
    lines=[]
    for stage,(action,source) in m.EXPECTED.items():
        lines.append(f"live source-aware {stage} planner: SOURCE_PLAN source={source} "
                     f"wheat_source=0 action={action} ML_MODEL_UNCHANGED EXECUTION_DISABLED")
        lines.append(f"REAL_SOURCE_PLAN stage={stage} action={action} "
                     f"source={source} read_only=true")
    return "\n".join(lines)

def main():
    base=fixture()
    assert len(m.parse(base)["stages"])==3
    invalid=[
        base.replace("read_only=true","read_only=false",1),
        base.replace("action=INSPECT_SOURCE","action=REQUEST_WHEAT_HAUL",1),
        base.replace("ML_MODEL_UNCHANGED","MODEL_TRAINED",1),
        base.replace("EXECUTION_DISABLED","EXECUTION_ENABLED",1),
        base.replace("source=EMPTY","source=AVAILABLE",1),
        base+"\n"+base.splitlines()[-1],
        "\n".join(base.splitlines()[:-2]),
    ]
    for text in invalid:
        try:m.parse(text)
        except ValueError:pass
        else:raise AssertionError("Invalid reference planning evidence accepted")
    print("PASS 8 partial-source planning evidence checks")
if __name__=="__main__":main()
