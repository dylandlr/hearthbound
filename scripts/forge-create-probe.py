#!/usr/bin/env python3
"""Assertions against an actual Forge server with released Create installed."""
import importlib.util
import pathlib

loader = importlib.util.spec_from_file_location(
    "rcon", pathlib.Path(__file__).with_name("forge-rcon-probe.py"))
module = importlib.util.module_from_spec(loader)
loader.loader.exec_module(module)

status = module.execute("hearthbound create_status")
print(status, flush=True)
for required in ("installed=true", "millstoneRegistered=true", "wheatFlourRegistered=true"):
    if required not in status:
        raise AssertionError("Missing Create runtime registry: " + status)
print("HB_CREATE_RUNTIME_PASS Create and required registries loaded", flush=True)

# Place a genuine Create block entity in a loaded test chunk. Unpowered is
# intentional: a powered scenario needs shafts, bearings and kinetic setup.
print(module.execute("forceload add 0 0"), flush=True)
placed = module.execute("setblock 0 100 0 create:millstone")
print(placed, flush=True)
inspection = module.execute("hearthbound inspect_mill 0 100 0")
print(inspection, flush=True)
if "HEARTHBOUND_CREATE_MILL_FOUND" not in inspection or "powered=false" not in inspection:
    raise AssertionError("Could not inspect an actual unpowered millstone: " + inspection)
print("HB_CREATE_MILL_INSPECTION_PASS genuine unpowered millstone", flush=True)

# Verify the bridge rejects a block that is not a millstone.
not_mill = module.execute("hearthbound inspect_mill 0 101 0")
print("Non-mill inspection:", not_mill, flush=True)
if "HEARTHBOUND_CREATE_MILL_FOUND" in not_mill:
    raise AssertionError("Create bridge falsely accepted non-mill block")

# A genuine millstone without kinetic input must remain unpowered.
for i in range(3):
    measured = module.execute("hearthbound inspect_mill 0 100 0")
    if "speed=0.0 RPM powered=false" not in measured:
        raise AssertionError("Unpowered millstone reported unexpected kinetic speed: " + measured)
print("HB_CREATE_NEGATIVE_PROBES_PASS non-mill rejected; 0 RPM stable", flush=True)

# Creative Motor is a test-only kinetic source. Place it below the millstone
# with its shaft facing upward, then interrogate the actual Create speed.
motor = module.execute("setblock 0 99 0 create:creative_motor[facing=up]")
print("Motor:", motor, flush=True)
import time
for attempt in range(25):
    time.sleep(1)
    measured = module.execute("hearthbound inspect_mill 0 100 0")
    if "powered=true" in measured and "speed=0.0 RPM" not in measured:
        print(measured, flush=True)
        print("HB_CREATE_POWERED_MILL_PASS real nonzero kinetic speed", flush=True)
        break
else:
    raise AssertionError("Create millstone did not receive power from creative motor: " + measured)

# Power-off regression: removing the motor must stop the same millstone.
print("Motor removed:", module.execute("setblock 0 99 0 air"), flush=True)
for attempt in range(25):
    time.sleep(1)
    measured = module.execute("hearthbound inspect_mill 0 100 0")
    if "speed=0.0 RPM powered=false" in measured:
        print("HB_CREATE_POWER_CUTOFF_PASS motor removed and millstone stopped", flush=True)
        break
else:
    raise AssertionError("Millstone stayed powered after motor removal: " + measured)

# Expose actual Create block-entity NBT for designing inventory-safe wheat processing.
nbt = module.execute("hearthbound ci_mill_nbt 0 100 0")
print(nbt[:2500], flush=True)
if "HB_MILL_NBT" not in nbt:
    raise AssertionError("Could not read real Create millstone NBT: " + nbt)
print("HB_CREATE_NBT_PROBE_PASS", flush=True)

# First genuine grinding experiment: seed the actual Create input inventory
# using vanilla /data merge, restore kinetic power, and inspect actual output.
wheat = module.execute('data merge block 0 100 0 {InputInventory:{Size:1,Items:[{Slot:0b,id:"minecraft:wheat",Count:4b}]}}')
print("Wheat staging:", wheat, flush=True)
seeded = module.execute("hearthbound ci_mill_nbt 0 100 0")
print("Seeded NBT:", seeded[:1800], flush=True)
if "minecraft:wheat" not in seeded:
    raise AssertionError("Create millstone did not accept staged wheat: " + seeded)
print("Motor restored:", module.execute("setblock 0 99 0 create:creative_motor[facing=up]"), flush=True)
for attempt in range(90):
    time.sleep(1)
    processing = module.execute("hearthbound ci_mill_nbt 0 100 0")
    if "create:wheat_flour" in processing:
        print("HB_CREATE_WHEAT_GRINDING_PASS " + processing[:1800], flush=True)
        break
else:
    raise AssertionError("Create never produced wheat flour from four input wheat: " + processing)
