#!/usr/bin/env python3
"""Run-cohort control identity and no-generalization contract."""
import json
import tempfile
from pathlib import Path
from capture_real_forge_world_provenance import provenance
from validate_real_forge_run_cohort import cohort

def main():
    props="level-seed=seed-A\nlevel-name=smoke-world\nonline-mode=false\nenable-rcon=true\n"
    with tempfile.TemporaryDirectory() as name:
        a,b=Path(name)/"scripted.json",Path(name)/"trained.json"
        a.write_text(json.dumps(provenance(props,"SCRIPTED","chest-two-source-v1")))
        b.write_text(json.dumps(provenance(props,"TRAINED_MLP","chest-two-source-v1")))
        same=cohort([a,b])
        assert same["shared_seed_control_only"] and same["configured_distinct_seeds"]==1
        assert same["independent_world_conditions_verified"] is False
        assert same["generalization_claim_allowed"] is False
        props2=props.replace("seed-A","seed-B")
        b.write_text(json.dumps(provenance(props2,"TRAINED_MLP","chest-two-source-v1")))
        different=cohort([a,b])
        assert different["configured_distinct_seeds"]==2
        assert different["shared_seed_control_only"] is False
        assert different["independent_world_conditions_verified"] is False
        try:cohort([a,a])
        except ValueError:pass
        else:raise AssertionError("duplicated policy arm was accepted")
        forged=json.loads(b.read_text())
        forged["independent_world_sample_claimed"]=True
        b.write_text(json.dumps(forged))
        try:cohort([a,b])
        except ValueError:pass
        else:raise AssertionError("forged independence accepted")
    print("FORGE_COHORT_PROVENANCE_TESTS_PASS")

if __name__=="__main__":
    main()
