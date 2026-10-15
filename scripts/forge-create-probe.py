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
restored_speed = module.execute("hearthbound inspect_mill 0 100 0")
print("Restored speed:", restored_speed, flush=True)
for attempt in range(90):
    time.sleep(1)
    processing = module.execute("hearthbound ci_mill_nbt 0 100 0")
    if attempt in (0, 4, 14, 29, 59):
        print("Grinding sample", attempt, processing[:1400], flush=True)
    if "create:wheat_flour" in processing:
        print("HB_CREATE_WHEAT_GRINDING_PASS " + processing[:1800], flush=True)
        break
else:
    raise AssertionError("Create never produced wheat flour from four input wheat: " + processing)

# Exercise Forge automation interface on a different fresh millstone, not /data merge.
print(module.execute("setblock 2 100 0 create:millstone"), flush=True)
feed = module.execute("hearthbound ci_mill_feed 2 100 0 4")
print("Forge item handler feed:", feed, flush=True)
if "HB_CREATE_WHEAT_INSERTED amount=4" not in feed:
    raise AssertionError("Real millstone item capability rejected wheat: " + feed)
input_state = module.execute("hearthbound ci_mill_nbt 2 100 0")
if "minecraft:wheat" not in input_state:
    raise AssertionError("Capability insertion did not reach Create inventory: " + input_state)
print("HB_CREATE_CAPABILITY_INPUT_PASS", flush=True)

# Transfer inventory from a real vanilla barrel into an actual Create machine.
print(module.execute("setblock 4 100 0 barrel"), flush=True)
print(module.execute('data merge block 4 100 0 {Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]}'), flush=True)
print(module.execute("setblock 6 100 0 create:millstone"), flush=True)
supply = module.execute("hearthbound ci_mill_supply 4 100 0 6 100 0 4")
print("Mill supply:", supply, flush=True)
if "HB_MILL_SUPPLY_PASS barrel_removed=4 mill_inserted=4" not in supply:
    raise AssertionError("Barrel-to-Create supply failed: " + supply)
remaining = module.execute("data get block 4 100 0 Items")
inserted = module.execute("hearthbound ci_mill_nbt 6 100 0")
if not __import__("re").search(r"Count:\s*4b", remaining) or "minecraft:wheat" not in inserted:
    raise AssertionError("Barrel-to-Create supply inventories incorrect: " + remaining + " " + inserted)
print("HB_CREATE_BARREL_SUPPLY_PASS source=4 mill=4", flush=True)

# Citizen-operated end-to-end production on an isolated walkable stone platform.
# No direct injection or test-only instantaneous supply command in this scenario.
print("Citizen mill chunk ticket:", module.execute("forceload add 16 16 47 31"), flush=True)
print(module.execute("fill 20 99 20 34 99 22 minecraft:stone"), flush=True)
print(module.execute("setblock 23 100 21 minecraft:barrel"), flush=True)
print(module.execute('data merge block 23 100 21 {Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]}'), flush=True)
print(module.execute("setblock 31 100 21 create:millstone"), flush=True)
print(module.execute("setblock 31 99 21 create:creative_motor[facing=up]"), flush=True)
print(module.execute('summon minecraft:villager 21 100 21 {Tags:["hearthbound.sable"],PersistenceRequired:1b}'), flush=True)
job = module.execute("execute positioned 21 100 21 run hearthbound haul_sable 23 100 21 31 100 21 4")
print("Sable mill assignment:", job, flush=True)
if "Sable assigned" not in job:
    raise AssertionError("Sable could not accept Create hauling job: " + job)

for attempt in range(100):
    time.sleep(1)
    supply_source = module.execute("data get block 23 100 21 Items")
    production = module.execute("hearthbound ci_mill_nbt 31 100 21")
    if attempt in (0, 9, 19, 39, 69):
        print("Citizen mill speed:", module.execute("hearthbound inspect_mill 31 100 21"), flush=True)
        progress = module.execute("execute positioned 21 100 21 run hearthbound haul_status")
        villagers = module.execute('execute as @e[type=minecraft:villager,tag=hearthbound.sable,x=21,y=100,z=21,distance=..25,limit=1,sort=nearest] run data get entity @s Pos')
        print("Sable milling tick", attempt, supply_source[:300], production[:700], "job:", progress, "pos:", villagers, flush=True)
    if __import__("re").search(r"Count:\s*4b", supply_source) and "create:wheat_flour" in production:
        print("HB_SABLE_CREATE_FIRST_MILL_PASS real_citizen_haul_and_flour", flush=True)
        break
else:
    raise AssertionError("Sable did not supply wheat and produce flour: " + supply_source + " " + production)

# Output collection: ensure real flour is removed from Create's output and stored.
print(module.execute("setblock 33 100 21 minecraft:barrel"), flush=True)
collected = module.execute("hearthbound ci_flour_collect 31 100 21 33 100 21 1")
print("Flour collection:", collected, flush=True)
if "HB_FLOUR_COLLECTED count=1" not in collected:
    raise AssertionError("Create flour output capability collection failed: " + collected)
stockpile = module.execute("data get block 33 100 21 Items")
print("Flour stockpile:", stockpile, flush=True)
if "create:wheat_flour" not in stockpile:
    raise AssertionError("Flour never reached real storage barrel: " + stockpile)
print("HB_CREATE_FLOUR_STOCKPILE_PASS", flush=True)

# Verify villager-carried flour using a *new* output barrel, not direct collection.
# Original Create mill at (0,100,0) has previously produced flour.
print(module.execute("setblock 7 100 0 minecraft:barrel"), flush=True)
print(module.execute("fill -2 99 -2 9 99 3 minecraft:stone"), flush=True)
print(module.execute('summon minecraft:villager 0 100 2 {Tags:["hearthbound.sable"],PersistenceRequired:1b}'), flush=True)
pickup = module.execute("execute positioned 0 100 2 run hearthbound haul_flour 0 100 0 7 100 0 1")
print("Flour courier:", pickup, flush=True)
if "Sable assigned to collect flour" not in pickup:
    raise AssertionError("No Sable assigned to retrieve flour: " + pickup)
saw_flour_cargo = False
for attempt in range(80):
    time.sleep(1)
    courier_view = module.execute("execute positioned 0 100 2 run hearthbound worker_view")
    if "cargo=1 item=create:wheat_flour" in courier_view:
        saw_flour_cargo = True
    storage = module.execute("data get block 7 100 0 Items")
    if "create:wheat_flour" in storage:
        if not saw_flour_cargo:
            raise AssertionError("Flour courier never exposed its in-flight cargo: " + courier_view)
        print("HB_SABLE_FLOUR_COURIER_PASS " + storage, flush=True)
        print("HB_FLOUR_CARGO_VIEW_PASS", flush=True)
        break
else:
    raise AssertionError("Sable did not bring flour to stockpile: " + storage)

# Work-order test: only the initial order is player-issued.
print("Worker-chunk ticking:", module.execute("forceload add 48 48 66 52"), flush=True)
print(module.execute("fill 48 99 48 66 99 52 minecraft:stone"), flush=True)
print(module.execute("setblock 51 100 50 minecraft:barrel"), flush=True)
print(module.execute('data merge block 51 100 50 {Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]}'), flush=True)
print(module.execute("setblock 59 100 50 create:millstone"), flush=True)
print(module.execute("setblock 59 99 50 create:creative_motor[facing=up]"), flush=True)
print(module.execute("setblock 63 100 50 minecraft:barrel"), flush=True)
print(module.execute('summon minecraft:villager 49 100 50 {Tags:["hearthbound.sable"],PersistenceRequired:1b}'), flush=True)
order = module.execute("execute positioned 49 100 50 run hearthbound mill_order 51 100 50 59 100 50 63 100 50")
print("Work order:", order, flush=True)
if "First Mill work order enabled" not in order:
    raise AssertionError("Order registration failed: " + order)
for attempt in range(140):
    time.sleep(1)
    flour_stock = module.execute("data get block 63 100 50 Items")
    wheat_stock = module.execute("data get block 51 100 50 Items")
    if attempt in (0, 2, 5, 15, 45, 90):
        print("Work order sample", attempt, wheat_stock[:250], flour_stock[:250], "machine:", module.execute("hearthbound ci_mill_nbt 59 100 50")[:650], "order:", module.execute("data get entity @e[type=minecraft:villager,tag=hearthbound.sable,x=49,y=100,z=50,distance=..20,sort=nearest,limit=1] ForgeData")[:1000], "position:", module.execute("data get entity @e[type=minecraft:villager,tag=hearthbound.sable,x=49,y=100,z=50,distance=..20,sort=nearest,limit=1] Pos"), "ticks:", module.execute("execute as @e[type=minecraft:villager,tag=hearthbound.sable,x=49,y=100,z=50,distance=..20,sort=nearest,limit=1] run data get entity @s Age"), flush=True)
    if "create:wheat_flour" in flour_stock and "Count: 8b" not in wheat_stock:
        print("HB_FIRST_MILL_WORK_ORDER_PASS", flush=True)
        # Keep the same order active and demand a second physical flour delivery.
        for extra in range(140):
            time.sleep(1)
            second = module.execute("data get block 63 100 50 Items")
            if extra in (0, 20, 60, 100):
                print("Second cycle sample", extra, second[:400], flush=True)
            if __import__("re").search(r'create:wheat_flour", Count:\s*[2-9]b', second):
                print("HB_FIRST_MILL_SECOND_CYCLE_PASS", flush=True)
                current = module.execute("execute positioned 49 100 50 run hearthbound mill_order_status")
                print("Active work order:", current, flush=True)
                if "First Mill: state=" not in current:
                    raise AssertionError("Work-order management status unavailable: " + current)
                break
        else:
            raise AssertionError("First Mill did not autonomously collect a second flour: " + second)
        break
else:
    raise AssertionError("Autonomous milling did not fill stockpile: " + wheat_stock + " " + flour_stock)

# Production cap: stockpile already has at least two flour. Setting target=1
# must make the order report TARGET_REACHED without taking more wheat.
cap = module.execute("execute positioned 49 100 50 run hearthbound mill_order_target 1")
print("Flour target command:", cap, flush=True)
if "First Mill flour target set to 1" not in cap:
    raise AssertionError("Production target command rejected order: " + cap)
for attempt in range(30):
    time.sleep(1)
    wait_status = module.execute("execute positioned 49 100 50 run hearthbound mill_order_status")
    if "TARGET_REACHED" in wait_status and "waitState=AT_WAIT" in wait_status:
        break
else:
    raise AssertionError("Worker did not return to its waiting spot: " + wait_status)
target_state = module.execute("execute positioned 49 100 50 run hearthbound mill_order_status")
print("Flour capped status:", target_state, flush=True)
if "TARGET_REACHED" not in target_state:
    raise AssertionError("Scheduler did not honor flour stockpile target: " + target_state)
print("HB_FIRST_MILL_TARGET_PASS", flush=True)
target_view = module.execute("execute positioned 49 100 50 run hearthbound worker_view")
print("Target presentation:", target_view, flush=True)
stocked = __import__("re").search(r"flour=(\d+)", target_view)
if "activity=target_reached cargo=0" not in target_view or "target=1" not in target_view or not stocked or int(stocked[1]) < 2:
    raise AssertionError("Worker presentation lost actual stock/target: " + target_view)
print("HB_WORKER_PROGRESS_VIEW_PASS", flush=True)

# Waiting-point commands and physical return, without changing target or stocks.
worker = "@e[type=minecraft:villager,tag=hearthbound.sable,x=49,y=100,z=50,distance=..25,sort=nearest,limit=1]"
prefix = "execute positioned 49 100 50 run hearthbound "
before = (module.execute("data get block 51 100 50 Items"), module.execute("data get block 63 100 50 Items"))
assert "waiting spot set" in module.execute(prefix + "mill_order_wait 49 100 52")
assert "Choose clear floor" in module.execute(prefix + "mill_order_wait 51 100 50")

def await_wait(state):
    for attempt in range(35):
        time.sleep(.5)
        status = module.execute(prefix + "mill_order_status")
        if "waitState=" + state in status:
            return status
    raise AssertionError("Waiting spot did not reach " + state + ": " + status)

def assert_feet(x, z):
    import re
    pos = module.execute("data get entity " + worker + " Pos")
    coords = [float(n) for n in re.findall(r"(-?\d+(?:\.\d+)?)d", pos)]
    assert len(coords) == 3 and int(coords[0] // 1) == x and int(coords[1] // 1) == 100 and int(coords[2] // 1) == z, pos

assert "wait=49, 100, 52" in await_wait("AT_WAIT")
assert_feet(49, 52)
# Choose a distant clear point, then obstruct its head space before arrival.
assert "waiting spot set" in module.execute(prefix + "mill_order_wait 55 100 52")
module.execute("setblock 55 101 52 minecraft:stone")
await_wait("BLOCKED")
blocked_view = module.execute(prefix + "worker_view")
assert "activity=wait_blocked cargo=0" in blocked_view, blocked_view
assert before == (module.execute("data get block 51 100 50 Items"), module.execute("data get block 63 100 50 Items"))
module.execute("setblock 55 101 52 minecraft:air")
assert "wait=55, 100, 52" in await_wait("AT_WAIT")
assert_feet(55, 52)
time.sleep(2)
assert_feet(55, 52)
assert before == (module.execute("data get block 51 100 50 Items"), module.execute("data get block 63 100 50 Items"))
print("HB_WORKSHOP_WAITING_PASS physical_return invalid_point blocked_head automatic_retry stable_stocks", flush=True)

# Stop only after production-target validation, preserving the active work order.
stopped = module.execute("execute positioned 49 100 50 run hearthbound mill_order_stop")
print("Stopped work order:", stopped, flush=True)
if "First Mill scheduling stopped" not in stopped:
    raise AssertionError("Could not disable work-order scheduling: " + stopped)
print("HB_FIRST_MILL_CONTROLS_PASS", flush=True)

# Commands must target the same nearest eligible citizen in a multi-worker colony.
selection_spec = importlib.util.spec_from_file_location(
    "worker_selection", pathlib.Path(__file__).with_name("worker-selection-probe.py"))
selection = importlib.util.module_from_spec(selection_spec)
selection_spec.loader.exec_module(selection)
selection.run(module.execute)
