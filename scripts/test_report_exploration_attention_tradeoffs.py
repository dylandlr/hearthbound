#!/usr/bin/env python3
"""Reject fabricated aggregated exploration-policy claims."""
import copy
from benchmark_exploration_aware_attention import benchmark
from report_exploration_attention_tradeoffs import summarize,canonical
import hashlib

def reject(item):
    try:summarize(item)
    except ValueError:return
    raise AssertionError("invalid exploration evidence accepted")

def resign(x):
    x.pop("sha256",None)
    x["sha256"]=hashlib.sha256(canonical(x).encode()).hexdigest()
    return x

def main():
    x=benchmark((3,5,7),12,3)
    a=summarize(x)
    assert a==summarize(x)
    assert a["total_evaluation_cases"]==36
    assert len(a["regimes"])==4
    assert not a["model_promotion_authorized"]
    assert not a["real_forge_outcomes_used"]
    assert set(a["aggregate"])=={
        "legacy_style","mixed_rapid_curriculum","exploration_aware"}
    bad=copy.deepcopy(x)
    bad["model_promotion_authorized"]=True
    reject(resign(bad))
    bad=copy.deepcopy(x)
    bad["cases"][0]["differences"]["exploration_aware"]["mean_neural_minus_scripted_discoveries"]=9
    reject(resign(bad))
    bad=copy.deepcopy(x)
    bad["cases"][0]["training_seed"]=bad["cases"][12]["training_seed"]
    reject(resign(bad))
    bad=copy.deepcopy(x)
    bad["cases"][0]["differences"]["exploration_aware"]["episodes_better_than_scripted"]+=1
    reject(resign(bad))
    bad=copy.deepcopy(x)
    bad["cases"].pop()
    reject(resign(bad))
    print("EXPLORATION_ATTENTION_TRADEOFF_AUDIT_CONTRACT_PASS")

if __name__=="__main__":
    main()
