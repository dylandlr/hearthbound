#!/usr/bin/env python3
"""Protect uncertainty-objective admission from fabricated synthetic results."""
import copy
import hashlib
from benchmark_observed_uncertainty_objective import benchmark
from report_observed_uncertainty_admission import audit,canonical

def denied(report):
    try:audit(report)
    except ValueError:return
    raise AssertionError("invalid objective evidence accepted")

def resign(x):
    x.pop("sha256",None)
    x["sha256"]=hashlib.sha256(canonical(x).encode()).hexdigest()
    return x

def main():
    x=benchmark((3,5,7),12,3)
    a=audit(x)
    assert a==audit(x)
    assert len(a["seed_results"])==3
    assert len(a["regime_results"])==4
    assert not a["minecraft_model_promotion_authorized"]
    assert not a["real_forge_generalization_established"]
    assert a["candidate_passed_simulator_admission"]==(
        a["seed_consistency_passed"] and a["regime_robustness_passed"])
    changed=copy.deepcopy(x)
    changed["model_promotion_authorized"]=True
    denied(resign(changed))
    changed=copy.deepcopy(x)
    changed["cases"].pop()
    denied(resign(changed))
    changed=copy.deepcopy(x)
    changed["cases"][0]["mean_neural_minus_scripted_discoveries"]["uncertainty_neural"]=20.
    denied(resign(changed))
    changed=copy.deepcopy(x)
    changed["cases"][0]["train_seed"]=changed["cases"][12]["train_seed"]
    denied(resign(changed))
    print("UNCERTAINTY_OBJECTIVE_ADMISSION_CONTRACT_PASS")

if __name__=="__main__":
    main()
