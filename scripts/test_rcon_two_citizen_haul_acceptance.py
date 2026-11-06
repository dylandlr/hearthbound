#!/usr/bin/env python3
"""Fail-closed contract tests for two-villager physical hauling acceptance.

The fake transport tests that the runner insists on operator-visible physical
Minecraft receipts. It is not a substitute for the real Forge server workflow.
"""
import ast
from pathlib import Path
from rcon_two_citizen_haul_acceptance import (
    run_trial,CHECK_DEST_A,CHECK_DEST_B,CITIZEN_A,CITIZEN_B)

class WorldResponses:
    def __init__(self,conflict_rejected=True,both_deliver=True,claims_release=True):
        self.commands=[]
        self.count_checks=0
        self.polls=0
        self.conflict_rejected=conflict_rejected
        self.both_deliver=both_deliver
        self.claims_release=claims_release
    def run(self,cmd):
        self.commands.append(cmd)
        if cmd=="hearthboundclaims count":
            self.count_checks+=1
            n=(1 if self.count_checks==1 else
               2 if self.count_checks==2 else
               0 if self.claims_release else 1)
            return f"Active source claims in this dimension: {n}"
        if cmd==CITIZEN_B+"sable haul 11 100 1 19 100 1":
            return ("source already claimed by another citizen" if
                    self.conflict_rejected else "Sable assigned wheat haul")
        if cmd==CHECK_DEST_A or cmd==CHECK_DEST_B:
            if cmd==CHECK_DEST_B:
                self.polls+=1
            if self.polls>=2 and (self.both_deliver or cmd==CHECK_DEST_A):
                return "Test passed, count: 1"
            return "Test failed"
        if "sable haul-audit" in cmd:
            pos=11 if cmd.startswith(CITIZEN_A) else 24
            return f"AUDIT job=fake-test-only source=BlockPos{{x={pos}, y=100, z=1}} claim=owned"
        if "hearthboundclaims owner" in cmd:
            return "No source claim" if self.count_checks>=3 else "Claim at source belongs to id"
        if "execute if data block" in cmd or "execute positioned" in cmd and " if entity " in cmd:
            return "Test passed, count: 1"
        if cmd.startswith("forceload "):return "Marked chunk to be force loaded"
        if cmd.startswith("fill "):return "Successfully filled 10 blocks"
        if cmd.startswith("setblock "):return "Changed the block"
        if cmd.startswith("data merge block "):return "Modified block data"
        if cmd.endswith("sable spawn"):return "Sable spawned"
        if cmd.endswith("sable haul 11 100 1 7 100 1") or cmd.endswith(
                "sable haul 24 100 1 19 100 1"):
            return "Sable assigned wheat haul"
        if cmd.startswith("execute if entity "):return "Test passed, count: 2"
        return "UNKNOWN_FAKE_COMMAND"
    def require(self,cmd,expected):
        output=self.run(cmd)
        if expected.lower() not in output.lower():
            raise AssertionError(f"Required physical receipt missing: {cmd} {output}")
        return output

def denies(fn):
    try:fn()
    except AssertionError:return
    raise AssertionError("mocked invalid server state was accepted")

def main():
    path=Path(__file__).with_name("rcon_two_citizen_haul_acceptance.py")
    src=path.read_text()
    ast.parse(src)
    assert 'sable haul 11 100 1 19 100 1' in src
    assert 'source already claimed by another citizen' in src
    assert 'hearthboundclaims count' in src
    assert 'hearthboundclaims owner 11 100 1' in src
    assert 'source_count_each=7 destination_count_each=1' in src
    assert 'model' not in src.lower()
    valid=WorldResponses()
    run_trial(valid,sleep=lambda _:None)
    assert valid.polls==3
    assert valid.count_checks==3
    assert any('sable haul-audit' in x for x in valid.commands)
    denies(lambda:run_trial(WorldResponses(conflict_rejected=False),
                            sleep=lambda _:None))
    denies(lambda:run_trial(WorldResponses(both_deliver=False),
                            sleep=lambda _:None))
    denies(lambda:run_trial(WorldResponses(claims_release=False),
                            sleep=lambda _:None))
    print("REAL_TWO_CITIZEN_ACCEPTANCE_CONTRACT_PASS conflicts physical_counts claim_release fail_closed")
if __name__=="__main__":
    main()
