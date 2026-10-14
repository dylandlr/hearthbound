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
