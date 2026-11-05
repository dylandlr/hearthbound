#!/usr/bin/env python3
"""Reject altered, incomplete or inflated recurrent-attention results."""
import copy
import hashlib
from benchmark_recurrent_causal_attention import benchmark
from report_recurrent_attention_admission import audit,canonical

def deny(data):
    try:audit(data)
    except ValueError:return
    raise AssertionError("invalid GRU evidence accepted")

def resign(data):
    data.pop("sha256",None)
    data["sha256"]=hashlib.sha256(canonical(data).encode()).hexdigest()
    return data

def main():
    data=benchmark((3,5,7),8,2)
    result=audit(data)
    assert result==audit(data)
    assert result["heldout_case_count"]==36
    assert result["training_seed_count"]==3
    assert result["model_promotion_authorized"] is False
    assert result["passed_simulator_admission"]==(
        result["seed_consistency_passed"] and result["regime_robustness_passed"])
    broken=copy.deepcopy(data)
    broken["cases"][0]["mean_vs_scripted"]["gru"]=30
    deny(resign(broken))
    broken=copy.deepcopy(data)
    broken["cases"][0]["train_seed"]=data["cases"][12]["train_seed"]
    deny(resign(broken))
    broken=copy.deepcopy(data)
    broken["cases"].pop()
    deny(resign(broken))
    broken=copy.deepcopy(data)
    broken["minecraft_model_promotion_authorized"]=True
    deny(resign(broken))
    print("RECURRENT_CAUSAL_ATTENTION_ADMISSION_CONTRACT_PASS")

if __name__=="__main__":
    main()
