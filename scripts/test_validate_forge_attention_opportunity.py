#!/usr/bin/env python3
"""Contract tests for source-choice telemetry without future information."""
import validate_forge_attention_opportunity as v

GOOD=("ATTENTION_OPPORTUNITY schema=hearthbound.forge-attention-opportunity.v1"
      " tick=100 observer=11111111-1111-4111-8111-111111111111"
      " dimension=minecraft:overworld candidates=10,100,2;9,100,2"
      " candidate_count=2 selected=9,100,2 budget=1"
      " policy=LEAST_RECENTLY_SAMPLED inventory_read=false action_authorized=false")

def rejected(raw):
    try:v.parse(raw)
    except ValueError:return
    raise AssertionError("unsafe opportunity accepted: "+raw)

def main():
    result=v.parse(GOOD)
    neural=v.parse(GOOD.replace(
        "policy=LEAST_RECENTLY_SAMPLED","policy=NEURAL_CAUSAL_MLP_OPT_IN"))
    assert neural["policy"]=="NEURAL_CAUSAL_MLP_OPT_IN"
    assert neural["inventory_read"] is False
    assert neural["action_authorized"] is False
    assert result["selected"] in result["candidates"]
    assert result["inventory_read"] is False
    assert result["counterfactual_outcomes_available"] is False
    for before,after in (
        ("inventory_read=false","inventory_read=true"),
        ("action_authorized=false","action_authorized=true"),
        ("candidate_count=2","candidate_count=3"),
        ("selected=9,100,2","selected=8,100,2"),
        ("budget=1","budget=2"),
        ("tick=100","tick=-1"),
        ("candidates=10,100,2;9,100,2","candidates=9,100,2;9,100,2"),
        ("policy=LEAST_RECENTLY_SAMPLED","policy=UNVERIFIED"),
    ):
        rejected(GOOD.replace(before,after))
    rejected(GOOD+" wheat=4")
    rejected(GOOD+" state=AVAILABLE")
    rejected(GOOD+" action_authorized=false")
    print("FORGE_ATTENTION_OPPORTUNITY_CONTRACT_PASS")

if __name__=="__main__":
    main()
