#!/usr/bin/env python3
"""World-seed and fixture provenance cannot be silently rewritten."""
from capture_real_forge_world_provenance import provenance

PROPS="level-name=smoke-world\nlevel-seed=independent-seed-A\nonline-mode=false\nenable-rcon=true\n"

def rejected(*args,**kwargs):
    try:provenance(*args,**kwargs)
    except ValueError:return
    raise AssertionError("invalid provenance accepted")

def main():
    x=provenance(PROPS,"SCRIPTED","chest-two-source-v1","independent-seed-A")
    y=provenance(PROPS,"TRAINED_MLP","chest-two-source-v1","independent-seed-A")
    assert x["world_seed_configured"]==y["world_seed_configured"]
    assert x["server_properties_sha256"]==y["server_properties_sha256"]
    assert x["world_generation_verified"] is False
    assert x["independent_world_sample_claimed"] is False
    assert x["neural_policy_executed"] is False
    rejected(PROPS,"SCRIPTED","chest-two-source-v1","different-seed")
    rejected(PROPS,"UNVERIFIED","chest-two-source-v1")
    rejected(PROPS,"SCRIPTED","../../escape")
    rejected(PROPS+"level-seed=duplicate\n","SCRIPTED","fixture")
    rejected(PROPS.replace("enable-rcon=true","enable-rcon=false"),"SCRIPTED","fixture")
    rejected(PROPS.replace("level-seed=independent-seed-A","level-seed="),"SCRIPTED","fixture")
    assert x==provenance(PROPS,"SCRIPTED","chest-two-source-v1","independent-seed-A")
    print("FORGE_WORLD_PROVENANCE_CONTRACT_PASS")

if __name__=="__main__":
    main()
