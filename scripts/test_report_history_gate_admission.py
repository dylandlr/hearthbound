#!/usr/bin/env python3
"""Admission audit regression: no promotion by positive pooled means."""
import copy
import hashlib
from benchmark_history_gated_attention import benchmark
from report_history_gate_admission import audit,canonical

def refused(x):
    try:audit(x)
    except ValueError:return
    raise AssertionError("invalid gate admission evidence accepted")

def resign(x):
    x.pop("sha256",None)
    x["sha256"]=hashlib.sha256(canonical(x).encode()).hexdigest()
    return x

def main():
    data=benchmark((3,5,7),12,3)
    result=audit(data)
    assert result==audit(data)
    assert result["training_seed_count"]==3
    assert result["heldout_case_count"]==36
    assert result["minecraft_model_promotion_authorized"] is False
    assert result["real_forge_generalization_established"] is False
    assert result["candidate_passed_simulator_admission"]==(
        result["seed_consistency_passed"] and result["regime_robustness_passed"])
    assert len(result["seed_breakdown"])==3
    assert len(result["regime_breakdown"])==4
    bad=copy.deepcopy(data)
    bad["minecraft_policy_deployed"]=True
    refused(resign(bad))
    bad=copy.deepcopy(data)
    bad["cases"][0]["gated_minus_scripted_mean"]=9
    refused(resign(bad))
    bad=copy.deepcopy(data)
    bad["cases"][0]["train_seed"]=data["cases"][12]["train_seed"]
    refused(resign(bad))
    bad=copy.deepcopy(data)
    bad["cases"].pop()
    refused(resign(bad))
    print("HISTORY_GATE_SIMULATOR_ADMISSION_CONTRACT_PASS")

if __name__=="__main__":
    main()
