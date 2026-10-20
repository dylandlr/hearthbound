#!/usr/bin/env python3
"""Static safety check for Minecraft CI workshop fixture ordering."""
from pathlib import Path

source=Path("scripts/rcon_autonomous_scientist.py").read_text()
floor='"fill 0 100 0 12 100 4 minecraft:spruce_planks"'
motor='"setblock 7 100 1 create:creative_motor[facing=up] replace"'
mill='"setblock 7 101 1 create:millstone replace"'
positions=[i for i in range(len(source)) if source.startswith(motor,i)]
assert floor in source and len(positions)>=2 and mill in source, "Workshop fixture missing real Create components"
assert positions[-1]>source.index(floor), "Workshop floor would overwrite the Create motor"
assert source.rfind(mill)>source.index(floor), "Workshop must restore Create millstone"
print("PASS: Create power source restored after scenery construction")
