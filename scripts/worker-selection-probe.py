#!/usr/bin/env python3
"""Multi-worker targeting regression against a disposable Forge + Create server."""
import importlib.util
from pathlib import Path
import time


def run(execute):
    def require(command, expected):
        result = execute(command)
        if expected not in result:
            raise AssertionError(command + ": " + result)
        return result

    # Spawn the farther worker first: entity iteration order must not decide targeting.
    execute("forceload add 160 160 191 175")
    execute("fill 160 99 160 186 99 168 minecraft:stone")
    execute("kill @e[tag=hb_selection_probe]")
    execute("setblock 172 100 165 minecraft:barrel")
    execute("setblock 175 100 165 create:millstone")
    execute("setblock 178 100 165 minecraft:barrel")
    for name, x in (("hb_far", 164), ("hb_near", 170)):
        require(f'summon minecraft:villager {x} 100 162 '
                f'{{Tags:["hearthbound.sable","hb_selection_probe","{name}"],'
                'NoAI:1b,PersistenceRequired:1b}', "Summoned new Villager")
    near = "@e[type=minecraft:villager,tag=hb_near,limit=1]"
    far = "@e[type=minecraft:villager,tag=hb_far,limit=1]"
    # Chunk block access can be ready before entity sections become visible to
    # level queries. Summon success alone does not establish a ticking worker.
    for _ in range(40):
        ready = execute(f"execute if entity {near} if entity {far} "
                        "run say HB_SELECTION_WORKERS_READY")
        if "HB_SELECTION_WORKERS_READY" in ready:
            break
        time.sleep(0.25)
    else:
        raise AssertionError("Selection fixture workers never became visible: "
                             + execute(f"data get entity {near} Pos") + " "
                             + execute(f"data get entity {far} Pos"))
    order = "hearthbound mill_order 172 100 165 175 100 165 178 100 165"
    require("execute positioned 170 100 162 run " + order, "work order enabled")
    require(f"data get entity {near} ForgeData.HearthboundMillOrder.Enabled", "1b")
    # An existing order excludes the nearer worker from a second assignment.
    require("execute positioned 170 100 162 run " + order, "work order enabled")
    require(f"data get entity {far} ForgeData.HearthboundMillOrder.Enabled", "1b")
    require("execute positioned 170 100 162 run hearthbound mill_order_target 7", "set to 7")
    require(f"data get entity {near} ForgeData.HearthboundMillOrder.TargetFlour", "7")
    require("execute positioned 164 100 162 run hearthbound mill_order_target 11", "set to 11")
    require("execute positioned 170 100 162 run hearthbound mill_order_status", "target=7")
    require("execute positioned 170 100 162 run hearthbound mill_order_stop", "scheduling stopped")
    require(f"data get entity {far} ForgeData.HearthboundMillOrder.TargetFlour", "11")
    absent = execute(f"data get entity {near} ForgeData.HearthboundMillOrder")
    if "Enabled" in absent:
        raise AssertionError("Stop retained the near worker's order: " + absent)
    # Busy nearest worker must not receive a new order.
    execute(f"data merge entity {near} {{ForgeData:{{HearthboundTravelActive:1b}}}}")
    rejected = execute("execute positioned 170 100 162 run " + order)
    if "No unassigned Sable" not in rejected:
        raise AssertionError("Busy workers were eligible: " + rejected)
    travel = execute("execute positioned 170 100 162 run hearthbound assign_sable 174 100 162")
    if "No idle Sable" not in travel:
        raise AssertionError("Travel replaced an existing worker job: " + travel)
    execute("kill @e[tag=hb_selection_probe]")
    print("HB_WORKER_SELECTION_PASS nearest_idle_start_target_status_stop", flush=True)


if __name__ == "__main__":
    spec = importlib.util.spec_from_file_location("rcon", Path(__file__).with_name("forge-rcon-probe.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    run(module.execute)
