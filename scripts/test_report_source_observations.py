#!/usr/bin/env python3
"""Synthetic parser checks, not proof of real Minecraft observations."""
import importlib.util
from pathlib import Path

p=Path(__file__).with_name("report_source_observations.py")
spec=importlib.util.spec_from_file_location("report_source_observations",p)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def fixture():
    return "\n".join([
        "real partial observation of empty source: SOURCE_OBSERVATION state=EMPTY wheat=0 reason=OBSERVED tick=11 EXECUTION_DISABLED",
        "REAL_SOURCE_OBSERVATION stage=empty state=EMPTY wheat=0",
        "real partial observation of unsupported source: SOURCE_OBSERVATION state=UNKNOWN wheat=0 reason=NO_BLOCK_ENTITY tick=12 EXECUTION_DISABLED",
        "REAL_SOURCE_OBSERVATION stage=unknown state=UNKNOWN wheat=0",
        "real partial observation after restoring wheat: SOURCE_OBSERVATION state=AVAILABLE wheat=1 reason=OBSERVED tick=13 EXECUTION_DISABLED",
        "REAL_SOURCE_OBSERVATION stage=available state=AVAILABLE wheat=1",
    ])

def main():
    valid=fixture()
    r=module.parse(valid)
    assert len(r["stages"])==3 and r["neural_model_updated"] is False
    invalid=[
        valid.replace("stage=available state=AVAILABLE","stage=available state=UNKNOWN"),
        valid.replace("stage=unknown state=UNKNOWN","stage=unknown state=AVAILABLE"),
        valid.replace("wheat=1","wheat=0"),
        valid.replace("reason=NO_BLOCK_ENTITY","reason=OBSERVED"),
        valid.replace("REAL_SOURCE_OBSERVATION stage=empty state=EMPTY wheat=0",""),
        valid+ "\nREAL_SOURCE_OBSERVATION stage=available state=AVAILABLE wheat=1",
        valid.replace("real partial observation after restoring wheat:","another label:"),
    ]
    for value in invalid:
        try:module.parse(value)
        except ValueError:pass
        else:raise AssertionError("Invalid source evidence accepted")
    print("PASS 8 source-observation evidence checks")

if __name__=="__main__":
    main()
