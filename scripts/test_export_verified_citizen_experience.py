#!/usr/bin/env python3
"""Causal, run-split and unknown-outcome contracts for Forge dataset export."""
import hashlib
import json
import tempfile
from pathlib import Path
from test_validate_forge_attention_journal import RUN,C,O,assemble
from export_verified_citizen_experience import export

def setup(root,pairs):
    journal=root/("attention-"+RUN+".jsonl")
    manifest=root/("attention-"+RUN+".manifest.json")
    contents=assemble(pairs)
    journal.write_text(contents)
    tip=json.loads(contents.splitlines()[-1])["sha256"]
    metadata={
        "schema":"hearthbound.attention-run-manifest.v1",
        "run_id":RUN,"journal_file":journal.name,
        "records":len(pairs),"final_hash":tip,
        "journal_sha256":hashlib.sha256(journal.read_bytes()).hexdigest(),
        "finalized":True,"action_authorized":False
    }
    manifest.write_text(json.dumps(metadata)+"\n")
    return journal,manifest

def run_tests():
    choice2=C.replace("tick=100","tick=105").replace("selected=9,100,2","selected=10,100,2")
    outcome2=O.replace("tick=100","tick=105").replace("selected=9,100,2","selected=10,100,2").replace("wheat=3","wheat=0").replace("state=AVAILABLE","state=EMPTY")
    choice3=C.replace("tick=100","tick=110")
    outcome3=O.replace("tick=100","tick=110").replace("wheat=3","wheat=2")
    with tempfile.TemporaryDirectory() as path:
        root=Path(path)
        journal,manifest=setup(root,[(C,O),(choice2,outcome2),(choice3,outcome3)])
        result=export(journal,manifest,minimum=3)
        assert result==export(journal,manifest,minimum=3)
        assert result["origin"]=="VERIFIED_REAL_FORGE_ATTENTION_JOURNAL"
        assert result["split_unit"]=="RUN_ID_NOT_EVENT"
        assert result["training_labels_inferred"] is False
        assert result["learning_performed"] is False
        assert len(result["transitions"])==3
        first,second,third=result["transitions"]
        assert all(x["status"]=="UNKNOWN" for x in first["candidate_history_before_choice"])
        # Prior choice of chest 9 does not reveal chest 10.
        second_prior={s["source"]:s for s in second["candidate_history_before_choice"]}
        assert second_prior["9,100,2"]["last_observed_wheat"]==3
        assert second_prior["10,100,2"]["status"]=="UNKNOWN"
        # On the third decision, histories are still separate and causal.
        third_prior={s["source"]:s for s in third["candidate_history_before_choice"]}
        assert third_prior["9,100,2"]["last_observed_wheat"]==3
        assert third_prior["9,100,2"]["age_ticks"]==10
        assert third_prior["10,100,2"]["last_observed_wheat"]==0
        assert third["selected_outcome"]["wheat"]==2
        assert third_prior["9,100,2"]["direct_observation_count"]==1
        assert all(x["unselected_outcomes"]=="UNKNOWN" and x["optimal_action_label"] is None
                   and x["counterfactual_reward"] is None and not x["new_action_authority"]
                   for x in result["transitions"])
        # A changed or truncated journal must not yield training material.
        journal.write_text(journal.read_text().splitlines()[0]+"\n")
        try:export(journal,manifest)
        except ValueError: pass
        else:raise AssertionError("truncated journal accepted")
    print("VERIFIED_CITIZEN_EXPERIENCE_CONTRACT_PASS")

if __name__=="__main__":
    run_tests()
