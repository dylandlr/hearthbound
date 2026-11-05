#!/usr/bin/env python3
"""Reject inactive, inconsistent or forged policy evidence."""
import copy
import hashlib
from benchmark_forecast_policy_gating import benchmark
from report_forecast_policy_admission import audit,canonical

def denied(report):
    try:audit(report)
    except ValueError:return
    raise AssertionError("accepted invalid policy evidence")

def resign(x):
    x.pop("sha256",None)
    x["sha256"]=hashlib.sha256(canonical(x).encode()).hexdigest()
    return x

def main():
    report=benchmark((3,5,7),8,2)
    summary=audit(report)
    assert summary==audit(report)
    assert summary["case_count"]==36
    assert summary["seed_count"]==3
    assert summary["minecraft_model_promotion_authorized"] is False
    for name,row in summary["policies"].items():
        assert row["passed_exploratory_admission"]==(
            row["neural_policy_effectively_active"]
            and row["positive_in_every_training_seed"]
            and row["nonnegative_in_every_regime"])
    bad=copy.deepcopy(report);bad["cases"].pop();denied(resign(bad))
    bad=copy.deepcopy(report)
    bad["cases"][0]["mean_vs_scripted"]["age_blend"]=99
    denied(resign(bad))
    bad=copy.deepcopy(report)
    bad["cases"][0]["frozen_model_sha256"]="invalid"
    denied(resign(bad))
    bad=copy.deepcopy(report)
    bad["cases"][0]["training_seed"]=report["cases"][12]["training_seed"]
    denied(resign(bad))
    bad=copy.deepcopy(report)
    bad["minecraft_model_promotion_authorized"]=True
    denied(resign(bad))
    print("FROZEN_FORECAST_POLICY_ADMISSION_CONTRACT_PASS")

if __name__=="__main__":
    main()
