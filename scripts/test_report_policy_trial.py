#!/usr/bin/env python3
"""Unit checks for strict task outcome report parser. These are NOT Minecraft evidence."""
import importlib.util
from pathlib import Path

spec=importlib.util.spec_from_file_location("trial_report",Path(__file__).with_name("report_policy_trial.py"))
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def main():
    marker=("REAL_CREATE_FLOUR_OBSERVED\n"
            "REAL_CITIZEN_EXPERIENCE_OBSERVED\n"
            "REAL_POLICY_SELECTED_SABLE_HAUL mode=TRAINED_MLP ...\n")
    row=("REAL_POLICY_TRIAL_RESULT mode=TRAINED_MLP completion=1 elapsed_ticks=126 "
         "verified_experience=1 flour_observed=1 executor=SableHauling\n")
    report=module.parse(marker+row,"TRAINED_MLP")
    assert report["minecraft_elapsed_ticks"]==126 and not report["comparative_advantage_demonstrated"]
    invalid=[
        (marker+row,"SCRIPTED"),
        (row,"TRAINED_MLP"),
        (marker+row+row,"TRAINED_MLP"),
        (marker+row.replace("completion=1","completion=0"),"TRAINED_MLP"),
        (marker+row.replace("elapsed_ticks=126","elapsed_ticks=0"),"TRAINED_MLP"),
        (marker+row.replace("executor=SableHauling","executor=Fake"),"TRAINED_MLP"),
    ]
    for content,mode in invalid:
        try:module.parse(content,mode)
        except ValueError:pass
        else:raise AssertionError("Invalid policy trial report accepted")
    print("PASS 7 policy trial evidence report checks")

if __name__=="__main__":main()
