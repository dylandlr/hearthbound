#!/usr/bin/env python3
"""Chronology and private observer-isolation tests for real-receipt replay."""
import copy
import replay_real_forge_chronology as replay

ID1="11111111-1111-4111-8111-111111111111"
ID2="22222222-2222-4222-8222-222222222222"

def receipt(tick,rev,amount,observer=ID1,source="6,100,2"):
    return {"schema":"hearthbound.live-perception-receipt.v1",
            "dimension":"minecraft:overworld","source":source,
            "revision":rev,"tick":tick,
            "state":"EMPTY" if amount==0 else "AVAILABLE",
            "wheat":amount,"observer":observer,
            "evidence":"REAL_FORGE_SOURCE_OBSERVATION",
            "action_authorized":"false"}

def fixture(events):
    return {"schema":"hearthbound.live-perception-replay-validation.v1",
            "task_execution_authorized":False,"receipts":len(events),
            "events":events}

def expect_reject(value):
    try:replay.replay(value)
    except ValueError:return
    raise AssertionError("unsafe or impossible receipt trace accepted")

def test_no_future_or_cross_citizen_leak():
    events=[receipt(5,1,0),receipt(10,2,4),
            receipt(10,1,2,observer=ID2),receipt(15,3,0)]
    result=replay.replay(fixture(events))
    assert result==replay.replay(fixture(copy.deepcopy(events)))
    timeline=result["timeline"]
    assert timeline[0]["before_receipt"]["status"]=="UNKNOWN"
    assert timeline[1]["before_receipt"]["known_wheat"]==0
    assert timeline[1]["before_receipt"]["age_ticks"]==5
    assert timeline[2]["before_receipt"]["status"]=="UNKNOWN"
    assert timeline[3]["before_receipt"]["known_wheat"]==4
    assert timeline[3]["before_receipt"]["observations"]==2
    assert timeline[3]["after_receipt"]["observed_changes"]==2
    assert all(x["action_authorized"] is False and
               x["counterfactual_reward_available"] is False for x in timeline)
    assert result["origin"]=="REAL_FORGE_VERIFIED_RECEIPTS"
    assert result["training_performed"] is False
    assert result["distinct_observer_sources"]==2

def test_strict_rejections():
    original=[receipt(5,1,0),receipt(10,2,4)]
    expect_reject(fixture([original[1],original[0]]))
    expect_reject(fixture([original[0],original[0]]))
    expect_reject(fixture([original[0],receipt(10,1,4)]))
    expect_reject(fixture([original[0],receipt(10,2,0)]))
    for field,value in (("evidence","SIMULATED"),
                        ("action_authorized","true"),
                        ("wheat",-1),("tick",-1)):
        bad=copy.deepcopy(original)
        bad[0][field]=value
        expect_reject(fixture(bad))
    bad=fixture(original)
    bad["receipts"]=1
    expect_reject(bad)
    bad=fixture(original)
    bad["task_execution_authorized"]=True
    expect_reject(bad)
    expect_reject(fixture([]))

if __name__=="__main__":
    test_no_future_or_cross_citizen_leak()
    test_strict_rejections()
    print("REAL_FORGE_CHRONOLOGICAL_SHADOW_TESTS_PASS")
