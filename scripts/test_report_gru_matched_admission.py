#!/usr/bin/env python3
"""Reject forged/incomplete matched-update GRU evidence."""
import copy
import hashlib
from benchmark_gru_matched_optimizer import benchmark
from report_gru_matched_admission import audit,canonical

def rejected(report):
    try:audit(report)
    except ValueError:return
    raise AssertionError("invalid matched-optimizer evidence accepted")

def resign(data):
    data.pop("sha256",None)
    data["sha256"]=hashlib.sha256(canonical(data).encode()).hexdigest()
    return data

def main():
    report=benchmark((3,5,7),8,2)
    result=audit(report)
    assert result==audit(report)
    assert result["case_count"]==36
    assert result["seed_count"]==3
    assert result["minecraft_model_promotion_authorized"] is False
    assert result["candidate_passed_simulator_admission"]==(
        result["bptt_better_in_every_seed"]
        and result["bptt_not_worse_than_scripted_in_every_seed"])
    tampered=copy.deepcopy(report)
    tampered["same_update_cadence"]=False
    rejected(resign(tampered))
    tampered=copy.deepcopy(report)
    tampered["cases"][0]["mean_vs_scripted"]["eight_step_bptt"]=20
    rejected(resign(tampered))
    tampered=copy.deepcopy(report)
    tampered["cases"][0]["seed"]=report["cases"][12]["seed"]
    rejected(resign(tampered))
    tampered=copy.deepcopy(report)
    tampered["cases"].pop()
    rejected(resign(tampered))
    print("MATCHED_GRU_ADMISSION_AUDIT_CONTRACT_PASS")

if __name__=="__main__":
    main()
