#!/usr/bin/env python3
"""Reject tampered or incomplete latency/coverage comparisons."""
import copy
import hashlib
from benchmark_attention_event_latency import benchmark
from report_attention_event_admission import audit,canonical

def reject(report):
    try:audit(report)
    except ValueError:return
    raise AssertionError("invalid event evidence accepted")

def resign(data):
    data.pop("sha256",None)
    data["sha256"]=hashlib.sha256(canonical(data).encode()).hexdigest()
    return data

def main():
    raw=benchmark((3,5,7),8,2)
    result=audit(raw)
    assert result==audit(raw)
    assert result["paired_schedule_cells"]==9
    assert result["model_promotion_authorized"] is False
    changed=copy.deepcopy(raw)
    changed["cells"].pop()
    reject(resign(changed))
    changed=copy.deepcopy(raw)
    changed["cells"][0]["paired_against_scripted"]["age_blend"][
        "censored_event_delay_differences"][0]+=10
    reject(resign(changed))
    changed=copy.deepcopy(raw)
    changed["model_promotion_authorized"]=True
    reject(resign(changed))
    changed=copy.deepcopy(raw)
    changed["cells"][0]["training_seed"]=raw["cells"][3]["training_seed"]
    reject(resign(changed))
    print("EVENT_ADMISSION_CENSORED_DELAY_AND_COVERAGE_CONTRACT_PASS")
if __name__=="__main__":
    main()
