#!/usr/bin/env python3
"""Validate that a Minecraft contention report contains inspectable RCON evidence."""
import json,re,sys
data=json.load(open(sys.argv[1],encoding="utf-8"))
assert data.get("mode","").startswith("operator-triggered"),"Wrong experiment type"
before=data["claim_owner_before"]
after=data["claim_owner_after_rejection"]
assert before==after and "belongs to" in before,"Contender stole claim"
assert re.search(r"\b0\s*\[hb_claim_test\]",data["rejected_command_score"]),"Contending command did not fail"
assert "No source claim" in data["claim_after_completion"],"Claim not released"
assert "minecraft:wheat" in data["source_after"] and "Count: 1b" in data["source_after"],"Incorrect source count"
assert "minecraft:wheat" in data["destination_after"],"No destination wheat"
print("PASS: ownership, rejection, release and physical inventory evidence")
