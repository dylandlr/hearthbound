#!/usr/bin/env python3
"""Fast checks for source contention proof parsing; no Minecraft launch."""
import re

def rejected(response):
    return re.search(r"\b0\s*\[hb_claim_test\]",response) is not None

assert rejected("#second has 0 [hb_claim_test]")
assert rejected("Score #second: 0 [hb_claim_test]")
assert not rejected("#second has 1 [hb_claim_test]")
assert not rejected("#second has 0 [other]")
print("PASS: contending command must return scoreboard command result=0")
