#!/usr/bin/env python3
"""Regression tests for auditable Minecraft shared-source contention reports."""
from pathlib import Path
import copy
import importlib.util
import tempfile
import json

spec=importlib.util.spec_from_file_location("contention","scripts/validate_contention_evidence.py")
# Validator uses CLI directly; exercise it in a subprocess.
import subprocess,sys
proof={
 "mode":"operator-triggered isolation test; not autonomous task selection",
 "claim_owner_before":"Claim at 4, 101, 8 belongs to 11111111-1111-1111-1111-111111111111",
 "claim_owner_after_rejection":"Claim at 4, 101, 8 belongs to 11111111-1111-1111-1111-111111111111",
 "rejected_command_score":"#second has 0 [hb_claim_test]",
 "claim_after_completion":"No source claim at 4, 101, 8",
 "source_after":'[{id: "minecraft:wheat", Count: 1b}]',
 "destination_after":'[{id: "minecraft:wheat", Count: 1b}]'
}
with tempfile.TemporaryDirectory() as directory:
    path=Path(directory)/"proof.json"
    def passes(data):
        path.write_text(json.dumps(data))
        return subprocess.run([sys.executable,"scripts/validate_contention_evidence.py",str(path)],
                              capture_output=True,text=True).returncode==0
    assert passes(proof), "Valid observed-evidence-shaped fixture rejected"
    for key,bad in (
      ("rejected_command_score","#second has 1 [hb_claim_test]"),
      ("claim_owner_after_rejection","Claim at 4, 101, 8 belongs to another-owner"),
      ("claim_after_completion","Claim at 4, 101, 8 belongs to 11111111-1111-1111-1111-111111111111"),
      ("source_after",'[{id: "minecraft:wheat", Count: 2b}]'),
      ("destination_after","[]"),
    ):
        invalid=copy.deepcopy(proof)
        invalid[key]=bad
        assert not passes(invalid), "Invalid contention evidence accepted: "+key
print("PASS: contention validator rejects forged/contradictory proof fields")
