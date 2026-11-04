#!/usr/bin/env python3
"""Reject forged, misattributed, and counterfactual attention outcomes."""
from validate_forge_attention_pair import pair
from validate_forge_attention_opportunity import parse as parse_choice

C=("ATTENTION_OPPORTUNITY schema=hearthbound.forge-attention-opportunity.v1"
   " tick=100 observer=11111111-1111-4111-8111-111111111111"
   " dimension=minecraft:overworld candidates=10,100,2;9,100,2"
   " candidate_count=2 selected=9,100,2 budget=1"
   " policy=LEAST_RECENTLY_SAMPLED inventory_read=false action_authorized=false")
O=("ATTENTION_OUTCOME schema=hearthbound.forge-attention-outcome.v1"
   " tick=100 observer=11111111-1111-4111-8111-111111111111"
   " dimension=minecraft:overworld selected=9,100,2"
   " status=OBSERVED reason=VERIFIED state=AVAILABLE wheat=3"
   " evidence=REAL_FORGE_SOURCE_OBSERVATION action_authorized=false")

def denied(choice,outcome):
    try: pair(choice,outcome)
    except ValueError:return
    raise AssertionError("invalid decision/outcome pair was accepted")

def main():
    report=pair(C,O)
    assert report["outcome"]["wheat"]==3
    assert report["unselected_candidate_outcomes"]=="UNKNOWN"
    assert not report["counterfactual_reward_available"]
    assert not report["minecraft_actions_authorized"]
    for before,after in (
        ("tick=100","tick=105"),
        ("observer=11111111-1111-4111-8111-111111111111",
         "observer=22222222-2222-4222-8222-222222222222"),
        ("selected=9,100,2","selected=10,100,2"),
        ("dimension=minecraft:overworld","dimension=minecraft:the_nether"),
        ("action_authorized=false","action_authorized=true"),
        ("wheat=3","wheat=-1"),
        ("state=AVAILABLE","state=EMPTY"),
        ("reason=VERIFIED","reason=SENSOR_UNKNOWN"),
    ):
        denied(C,O.replace(before,after))
    for before,after in (
        ("status=OBSERVED reason=VERIFIED state=AVAILABLE wheat=3 evidence=REAL_FORGE_SOURCE_OBSERVATION",
         "status=UNOBSERVED reason=CHUNK_UNLOADED state=UNKNOWN wheat=-1 evidence=NO_VALID_OBSERVATION"),
    ):
        unknown=pair(C,O.replace(before,after))
        assert unknown["outcome"]["wheat"] is None
        assert unknown["outcome"]["state"] is None
    denied(C,O.replace("status=OBSERVED","status=UNOBSERVED"))
    denied(C,O+" alternative_wheat=99")
    denied(C+" wheat=99",O)
    print("REAL_FORGE_ATTENTION_PAIR_CONTRACT_PASS")

if __name__=="__main__":
    main()
