#!/usr/bin/env python3
"""Synthetic parser checks only; no simulated event counts as Minecraft evidence."""
import importlib.util
from pathlib import Path

path=Path(__file__).with_name("report_policy_rejection.py")
spec=importlib.util.spec_from_file_location("rejection",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def sample(mode):
    return (
      "real source shortage rejection: Source inventory has no real wheat\n"
      "no new hauling job after shortage: AUDIT job=xxx status=Haul complete\n"
      f"REAL_POLICY_TRIAL_REJECTION mode={mode} reason=SOURCE_NO_WHEAT "
      "dispatched=false credit=0 existing_job_unchanged=true\n"
      f"REAL_POLICY_SELECTED_SABLE_HAUL mode={mode} POLICY_TRIAL_ASSIGNED ...\n"
    )

def main():
    for mode in ("SCRIPTED","TRAINED_MLP"):
        record=mod.parse(sample(mode),mode)
        assert record["task_dispatched"] is False
        assert record["colony_task_reward"]==record["personal_task_reward"]==0
        assert record["training_transition"] is False
    base=sample("TRAINED_MLP")
    variants=[
      (base,"SCRIPTED"),
      (base.replace("dispatched=false","dispatched=true"),"TRAINED_MLP"),
      (base.replace("credit=0","credit=1"),"TRAINED_MLP"),
      (base.replace("existing_job_unchanged=true","existing_job_unchanged=false"),"TRAINED_MLP"),
      (base.replace("Source inventory has no real wheat",""),"TRAINED_MLP"),
      (base.replace("status=Haul complete","status=Walking to source"),"TRAINED_MLP"),
      (base+base,"TRAINED_MLP"),
      (base.replace("REAL_POLICY_SELECTED_SABLE_HAUL","OTHER_EVENT"),"TRAINED_MLP")
    ]
    for source,mode in variants:
        try:mod.parse(source,mode)
        except ValueError:pass
        else:raise AssertionError("Rejected invalid shortage receipt")
    print("PASS 10 real Minecraft refusal contract checks")
if __name__=="__main__":main()
