#!/usr/bin/env python3
"""Fail-closed configuration checks for actual Forge obstruction acceptance.

Does not claim to emulate Minecraft pathfinding. Real Forge integration must
construct and remove the obstruction and inspect inventories on the server.
"""
import ast
from pathlib import Path
from rcon_obstructed_haul_acceptance import (
    BARRIER,OPEN_BARRIER,POLL_SECONDS,MAX_POLLS,
    SOURCE_A,DEST_A,SOURCE_B,DEST_B,counts,inventory_empty,
    source_owned,source_unclaimed,audit_cargo)

class FakeRcon:
    def __init__(self,responses):
        self.responses=responses
        self.queries=[]
    def run(self,command):
        self.queries.append(command)
        return self.responses.get(command,"UNEXPECTED")
    def require(self,command,expected):
        output=self.run(command)
        if expected.lower() not in output.lower():
            raise AssertionError(f"Missing observed physical evidence: {command}: {output}")
        return output

def rejects(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError("false physical/memory claim accepted")

def main():
    script=Path(__file__).with_name("rcon_obstructed_haul_acceptance.py").read_text()
    ast.parse(script)
    assert BARRIER=="fill 9 100 0 9 102 2 minecraft:stone"
    assert OPEN_BARRIER=="fill 9 100 0 9 102 2 minecraft:air"
    assert (SOURCE_A,DEST_A,SOURCE_B,DEST_B)==(11,7,24,19)
    assert (MAX_POLLS,POLL_SECONDS)==(75,2)
    assert "rcon.require(BARRIER" not in script  # fixture builds barrier once
    assert "rcon.require(OPEN_BARRIER" in script
    assert "audit_cargo(rcon," in script
    assert "source_owned(rcon,SOURCE_A)" in script
    assert "source_unclaimed(rcon,SOURCE_A)" in script
    assert "inventory_empty(rcon,DEST_A)" in script
    assert "counts(rcon,SOURCE_B,DEST_B,7,1)" in script
    assert "if not recovered:raise AssertionError" in script
    assert "if not carrying or not b_delivered:" in script
    assert "REAL_FORGE_OBSTRUCTED_HAUL_PASS" in script
    chest='execute unless data block 7 100 1 Items[0]'
    empty=FakeRcon({chest:"Test passed, count: 1"})
    inventory_empty(empty,7)
    assert empty.queries==[chest]
    rejects(lambda:inventory_empty(FakeRcon({chest:"Test failed"}),7))
    rejected=FakeRcon({"hearthboundclaims owner 11 100 1":
                      "No source claim at 11, 100, 1"})
    rejects(lambda:source_owned(rejected,11))
    retained=FakeRcon({"hearthboundclaims owner 11 100 1":
                      "Claim at 11, 100, 1 belongs to uuid"})
    source_owned(retained,11)
    rejects(lambda:source_unclaimed(retained,11))
    correct=FakeRcon({
        "execute positioned 12 100 1 run sable haul-audit":
            "AUDIT job=abc phase=1 cargo=1xminecraft:wheat claim=owned"})
    audit_cargo(correct,"execute positioned 12 100 1 run ",1)
    stale=FakeRcon({
        "execute positioned 12 100 1 run sable haul-audit":
            "AUDIT job=abc phase=0 cargo=0xair claim=owned"})
    rejects(lambda:audit_cargo(stale,"execute positioned 12 100 1 run ",1))
    source='execute if data block 11 100 1 Items[{id:"minecraft:wheat",Count:7b}]'
    destination='execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]'
    observed=FakeRcon({source:"Test passed",destination:"Test passed"})
    counts(observed,11,7,7,1)
    rejects(lambda:counts(FakeRcon({
        source:"Test passed",destination:"Test failed"}),11,7,7,1))
    print("REAL_FORGE_OBSTRUCTED_ROUTE_CONTRACT_PASS "
          "held_cargo blocked_destination claims recovery physical_counts")

if __name__=="__main__":
    main()
