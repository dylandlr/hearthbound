#!/usr/bin/env python3
"""Forecast admission must not confuse calibration with policy success."""
import copy
import hashlib
from benchmark_observed_change_forecast import benchmark
from report_observed_change_admission import audit,canonical

def denied(r):
    try:audit(r)
    except ValueError:return
    raise AssertionError("invalid forecast evidence accepted")

def resign(r):
    r.pop("sha256",None)
    r["sha256"]=hashlib.sha256(canonical(r).encode()).hexdigest()
    return r

def main():
    report=benchmark((3,5,7),8,2)
    result=audit(report)
    assert result==audit(report)
    assert result["cases_checked"]==36
    assert result["minecraft_model_promotion_authorized"] is False
    assert result["candidate_passed_joint_simulator_admission"]==(
        result["prediction_better_than_history_on_average"]
        and result["policy_nonnegative_in_every_training_seed"]
        and result["policy_regime_robustness"])
    bad=copy.deepcopy(report);bad["cases"].pop();denied(resign(bad))
    bad=copy.deepcopy(report);bad["model_deployed_in_minecraft"]=True
    denied(resign(bad))
    bad=copy.deepcopy(report);bad["cases"][0]["forecast_policy_minus_scripted"]=31.
    denied(resign(bad))
    bad=copy.deepcopy(report)
    bad["cases"][0]["training_seed"]=bad["cases"][12]["training_seed"]
    denied(resign(bad))
    bad=copy.deepcopy(report)
    bad["cases"][0]["forecast"]["calibration_bins"][0]["count"]+=1
    denied(resign(bad))
    print("FORECAST_CALIBRATION_AND_POLICY_ADMISSION_CONTRACT_PASS")

if __name__=="__main__":
    main()
