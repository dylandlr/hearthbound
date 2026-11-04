#!/usr/bin/env python3
"""Causal safety contracts for observed-uncertainty objective."""
import copy
import math
from benchmark_observed_uncertainty_objective import (
    benchmark,preinspection_reward_terms,train_objective,evaluate_one,ARM_NAMES,WEIGHTS)
from benchmark_rapid_attention_curriculum import RapidWorld
from benchmark_exploration_aware_attention import train_exploration

def denied(call):
    try:call()
    except ValueError:return
    raise AssertionError("invalid historical source observation accepted")

def main():
    w=RapidWorld(101,"unequal_volatility",4)
    before=w.features()
    assert len(before)==16
    assert all(before[4*i]==1 for i in range(4))
    x=preinspection_reward_terms(w,0)
    assert x["first_inspection"]==1.
    assert x["rapid_reinspection"]==0.
    assert math.isclose(x["observed_history_uncertainty"],1.)
    w.inspect(0)
    after=w.features()
    assert all(after[4*i]==1 for i in (1,2,3))
    assert all(after[4*i+1]==0 for i in (1,2,3))
    assert preinspection_reward_terms(w,0)["first_inspection"]==0.
    assert preinspection_reward_terms(w,0)["rapid_reinspection"]==1.
    denied(lambda:preinspection_reward_terms(w,-1))
    w.observed_changes[0]=2
    denied(lambda:preinspection_reward_terms(w,0))
    denied(lambda:train_objective(5,0))
    denied(lambda:benchmark((3,3,5),12,3))
    denied(lambda:benchmark((3,5,7),0,3))
    denied(lambda:benchmark((3,5,7),12,0))
    candidate=train_objective(5,8)
    explorer=train_exploration(5,8)
    outcome=evaluate_one(90000,"high_volatility",4,{
        "uncertainty_neural":candidate,
        "exploration_neural":explorer})
    assert set(outcome)==set(ARM_NAMES)
    assert all(0<=outcome[k]["direct_discoveries"]<=32 for k in ARM_NAMES)
    a=benchmark((3,5,7),12,3)
    assert a==benchmark((3,5,7),12,3)
    assert a["evaluation_case_count"]==36
    assert a["origin"]=="SIMULATED_ONLY"
    assert a["unselected_truth_or_rewards_used_for_learning"] is False
    assert a["model_promotion_authorized"] is False
    assert a["forge_journal_used_for_training"] is False
    assert a["posterior_measures"]=="OBSERVED_DISAGREEMENT_NOT_TRUE_PER_TICK_HAZARD"
    assert set(a["objective_weights"])==set(WEIGHTS)
    for cell in a["cases"]:
        assert cell["heldout_episodes"]==3
        assert set(cell["policy_scores"])==set(ARM_NAMES)
        assert all(-32<=v<=32 for v in cell["mean_neural_minus_scripted_discoveries"].values())
    print("OBSERVED_UNCERTAINTY_OBJECTIVE_SIMULATOR_CONTRACT_PASS")

if __name__=="__main__":
    main()
