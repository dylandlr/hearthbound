#!/usr/bin/env python3
"""Regression for actual vanilla /data get chest item response."""
import re

def single_wheat_debit(text):
    return ('minecraft:wheat' in text and
            re.search(r'Count:[ ]*3b',text) is not None)

observed='3, 101, 7 has the following block data: [{Slot: 0b, id: "minecraft:wheat", Count: 3b}]'
assert single_wheat_debit(observed)
assert not single_wheat_debit(observed.replace("Count: 3b","Count: 4b"))
assert not single_wheat_debit(observed.replace("minecraft:wheat","minecraft:carrot"))
print("PASS: real Minecraft NBT source debit detected")
