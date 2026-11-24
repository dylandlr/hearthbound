#!/usr/bin/env python3
"""Real Forge/Create production, machine reuse, private learning, and restart.

This is a fixed engineering acceptance. It does not compare trained policies or
estimate causal communication benefit. All phases and failures remain in the
same artifact. Production quantities come from actual inventories and callbacks.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import time

from rcon_private_communication_trial import connection
from rcon_need_services_acceptance import records, require, response_json, validate_chain, xyz

COMMAND = "hearthbound-services"
SOURCE = (36, 101, 3)
MILL = (11, 101, 3)
MOTOR = (11, 100, 3)
BUFFER = (4, 101, 3)
INITIAL = 8
TARGET = 4
DEADLINE_SECONDS = 360
CLOSURE_GRACE_SECONDS = 35
QUIET_SECONDS = 15
SCHEMA = "hearthbound.production-service-live-acceptance.v1"
ALLOWED_OUTPUTS = {"create:wheat_flour", "minecraft:wheat_seeds"}


def inventory_items(text, allowed):
    """Read the independent native NBT list; counters are not inventories."""
    first, last = text.find("["), text.rfind("]")
    require(first >= 0 and last >= first, "Native inventory list missing: " + text)
    raw = text[first:last + 1]
    if raw.strip() == "[]":
        return {}
    ids = re.findall(r'\bid:\s*"([^"]+)"', raw)
    counts = re.findall(r"\bCount:\s*(-?\d+)b\b", raw)
    require(ids and len(ids) == len(counts), "Malformed native inventory: " + raw)
    require(all(item in allowed for item in ids), "Unexpected native item: " + raw)
    require(all(0 < int(count) <= 64 for count in counts), "Invalid native count: " + raw)
    result = Counter()
    for item, count in zip(ids, counts):
        result[item] += int(count)
    return dict(result)


def inventory(rcon, point, path="Items", allowed=ALLOWED_OUTPUTS):
    raw = rcon.run(f"data get block {xyz(point)} {path}")
    return {"position": list(point), "path": path,
            "items": inventory_items(raw, allowed), "native_response": raw}


def status(rcon):
    value = response_json(rcon.run(COMMAND + " status"), "NEED_SERVICES_STATUS")
    for name in ("enrolled", "assigned", "transfers", "held", "active_commitments",
                 "records_total", "production_jobs", "output_units", "cost_updates",
                 "production_credits", "capacity_denials"):
        require(type(value.get(name)) is int and value[name] >= 0, "Missing status count: " + name)
    require(type(value.get("enabled")) is bool, "Missing dispatch state")
    require(not value.get("failure") and not value.get("errors"), "Runtime failure: " + repr(value))
    require(value["capacity_denials"] == 0, "Bounded evidence capacity exhausted")
    return value


def unique(rows, kind, job):
    found = [row for row in rows if row.get("type") == kind and row.get("job") == job]
    require(len(found) == 1, f"Expected one {kind} for {job}, found {len(found)}")
    return found[0]


def validate_production_chain(rows):
    require([row.get("sequence") for row in rows] == list(range(1, len(rows) + 1)),
            "Missing or reordered production history")
    settled = [row for row in rows if row.get("type") == "PRODUCTION_SETTLED"]
    require(len(settled) >= 2, "Repeated physical production was not demonstrated")
    require(len({row.get("job") for row in settled}) == len(settled), "Duplicate productive job")
    require(len({row.get("physical_evidence") for row in settled}) == len(settled),
            "Duplicate final physical evidence")
    transport = validate_chain(rows, len(settled))
    items, prior_samples, owners = Counter(), {}, set()
    produced_by_citizen = Counter()
    linked_output = False
    for final in settled:
        job = final["job"]
        assigned = unique(rows, "MOTOR_ASSIGNED", job)
        transfer = unique(rows, "TRANSFER_VERIFIED", job)
        collected = unique(rows, "PRODUCTION_OUTPUT_COLLECTED", job)
        delivered = unique(rows, "PRODUCTION_OUTPUT_DELIVERED", job)
        service = unique(rows, "SERVICE_SETTLED", job)
        for row in (assigned, transfer, collected, delivered, service):
            for key in ("citizen", "request", "commitment", "session"):
                require(row.get(key) is not None and row[key] == final.get(key),
                        "Production changed ownership: " + key)
        require(assigned["sequence"] < transfer["sequence"] < collected["sequence"]
                < delivered["sequence"] < service["sequence"] < final["sequence"], "Production lifecycle reordered")
        require(transfer["delivered_tick"] <= collected["processing_start_tick"]
                < collected["process_tick"] <= collected["tick"] <= delivered["tick"] <= final["tick"],
                "Invalid processing/output chronology")
        require(collected["wheat_before"] == 1 and collected["wheat_after"] == 0,
                "Callback did not consume one real wheat")
        require(collected["flour_before"] == 0 and collected["flour_after"] > 0,
                "Missing independent flour delta")
        units = collected["flour_after"] - collected["flour_before"]
        require(type(units) is int and units == collected.get("units")
                == delivered.get("units") == final.get("units"), "Output quantity changed")
        require(delivered["stock_after"] - delivered["stock_before"] == units,
                "Destination insertion does not conserve flour")
        require(assigned.get("destination") == collected.get("machine") == list(MILL)
                and assigned.get("output_destination") == delivered.get("destination") == list(BUFFER),
                "Wrong physical machine/destination")
        require(assigned.get("source") == transfer.get("source") == list(SOURCE)
                and transfer.get("destination") == list(MILL), "Native input endpoints changed")
        require(final.get("physical_evidence") and job in final["physical_evidence"],
                "Final evidence is not tied to its native job")
        require(final["physical_evidence"] == collected.get("physical_evidence"),
                "Final evidence changed after output collection")
        require(final.get("reservation_released") is True and final.get("trace_retired") is True,
                "Completed machine cannot safely be reused")
        output = collected.get("items")
        require(isinstance(output, dict) and output.get("create:wheat_flour") == units,
                "Missing exact output cargo witness")
        require(set(output) <= ALLOWED_OUTPUTS and all(type(n) is int and n > 0 for n in output.values()),
                "Invalid output/byproduct witness")
        require(delivered.get("items") == final.get("items") == output,
                "Output or byproduct lost in transit or settlement")
        before_items, after_items = delivered.get("items_before"), delivered.get("items_after")
        require(isinstance(before_items, dict) and isinstance(after_items, dict),
                "Missing independent per-item insertion witnesses")
        for inventory in (before_items, after_items):
            require(set(inventory) <= ALLOWED_OUTPUTS
                    and all(type(n) is int and n > 0 for n in inventory.values()),
                    "Invalid destination item witness")
        expected_items = Counter(before_items)
        expected_items.update(output)
        require(dict(expected_items) == after_items, "Destination lost or fabricated a batch item")
        require(before_items.get("create:wheat_flour", 0) == delivered["stock_before"]
                and after_items.get("create:wheat_flour", 0) == delivered["stock_after"],
                "Scalar flour count differs from item witnesses")
        require(service.get("outcome") == "VERIFIED_TRANSFER"
                and service.get("tick") == delivered["tick"] == final["tick"]
                and service.get("service_samples") == final.get("service_samples"),
                "Learning did not settle the final physical service")
        require(type(service.get("started_tick")) is int
                and service["started_tick"] <= assigned["assigned_tick"]
                and service.get("duration_ticks") == service["tick"] - service["started_tick"],
                "Learning omitted part of the service duration")
        items.update(output)
        owner = final["citizen"]
        owners.add(owner)
        produced_by_citizen[owner] += units
        require(final.get("production_samples") == prior_samples.get(owner, 0) + 1,
                "Private output sample duplicated, missing, or pooled across citizens")
        prior_samples[owner] = final["production_samples"]
        require(final.get("service_samples", 0) >= final["production_samples"],
                "Production lacks settled complete-service duration")
        if assigned.get("origin") == "REPORT":
            require(final.get("selected_packet") == assigned.get("selected_packet"),
                    "Recipient production changed selected message")
            linked_output = True
    require(linked_output, "No received request led to actual recipient production")
    trained_decisions = [row for row in rows if row.get("type") == "POLICY_DECISION"
                         and any(score.get("production_samples", 0) > 0 for score in row.get("scores", []))]
    require(trained_decisions, "No subsequent live choice consulted a production-updated private model")
    for decision in trained_decisions:
        scores = decision["scores"]
        prior_output = [row for row in settled if row["citizen"] == decision.get("citizen")
                        and row["sequence"] < decision["sequence"]]
        require(prior_output and all(row["tick"] <= decision["tick"] for row in prior_output),
                "Decision consulted future or foreign production evidence")
        require(all(score.get("production_samples") == len(prior_output) for score in scores),
                "Decision model does not match its owner's evidence prefix")
        selected = [score for score in scores if score.get("id") == decision.get("selected")]
        require(len(selected) == 1, "Chosen candidate absent from logged private menu")
        require(selected[0]["total"] >= max(score["total"] for score in scores) - 1e-9,
                "Live selection bypassed its logged value scores")
        require(decision.get("citizen") in owners, "Citizen used somebody else's production model")
    return {**transport, "production_jobs": len(settled), "output_items": dict(items),
            "distinct_producers": len(owners), "recipient_production_chain": True,
            "output_units_by_citizen": dict(produced_by_citizen),
            "decisions_consulting_updated_model": len(trained_decisions),
            "causal_communication_benefit_estimated": False}


def setup(rcon):
    commands = (
        "gamerule doMobSpawning false", "gamerule doDaylightCycle false",
        "gamerule doWeatherCycle false", "time set 6000", "weather clear",
        "forceload add 0 0 47 15", "fill 0 100 0 44 105 6 minecraft:air",
        "fill 0 100 0 44 100 6 minecraft:stone",
        "fill 0 101 0 44 103 0 minecraft:stone", "fill 0 101 6 44 103 6 minecraft:stone",
        "fill 0 101 0 0 103 6 minecraft:stone", "fill 44 101 0 44 103 6 minecraft:stone",
        f'setblock {xyz(SOURCE)} minecraft:chest{{Items:[{{Slot:0b,id:"minecraft:wheat",Count:{INITIAL}b}}]}} replace',
        f"setblock {xyz(BUFFER)} minecraft:chest replace",
        f"setblock {xyz(MOTOR)} create:creative_motor[facing=up] replace",
        f"setblock {xyz(MILL)} create:millstone replace",
    )
    for command in commands:
        answer = rcon.run(command)
        require(not any(word in answer.lower() for word in
                        ("unknown command", "incorrect argument", "not loaded", "failed")),
                "Fixture setup failed: " + answer)
    power_deadline = time.monotonic() + 25
    while True:
        speed = rcon.run(f"data get block {xyz(MILL)} Speed")
        match = re.search(r"data: (-?\d+(?:\.\d+)?)f", speed)
        if match and abs(float(match.group(1))) > 0:
            break
        require(time.monotonic() < power_deadline, "Real mill did not receive kinetic power")
        time.sleep(.5)
    for tag, x in (("hb_production_a", 3), ("hb_production_b", 35)):
        rcon.require(f"execute positioned {x} 101 2 run sable spawn", "Sable spawned")
        selector = f"@e[type=minecraft:villager,name=Sable,x={x},y=101,z=2,distance=..4,limit=1,sort=nearest]"
        rcon.require(f"tag {selector} add {tag}", "Added tag")
        rcon.require(f"{COMMAND} enroll @e[tag={tag},limit=1]", "NEED_SERVICES_OK")
    rcon.require(f"{COMMAND} configure-mill {xyz(MILL)} {xyz(BUFFER)} {TARGET}", "NEED_SERVICES_OK")
    rcon.require(f"{COMMAND} configure-source {xyz(SOURCE)}", "NEED_SERVICES_OK")
    return {"source": inventory(rcon, SOURCE, allowed={"minecraft:wheat"}),
            "buffer": inventory(rcon, BUFFER), "power": speed}


def output_witnesses(rcon, jobs, items):
    source = inventory(rcon, SOURCE, allowed={"minecraft:wheat"})
    buffer = inventory(rcon, BUFFER)
    mill_input = inventory(rcon, MILL, "InputInventory.Items", {"minecraft:wheat"})
    mill_output = inventory(rcon, MILL, "OutputInventory.Items")
    require(source["items"].get("minecraft:wheat", 0) == INITIAL - jobs,
            "Source consumption differs from real processing count")
    require(buffer["items"] == items, "Native destination does not equal all delivered output/byproducts")
    require(not mill_input["items"] and not mill_output["items"], "Completed mill retained material")
    rcon.require(f"sable mill-reservation {xyz(MILL)}", "MILL_RESERVATION NONE")
    rcon.require("hearthboundclaims count", "Active source claims in this dimension: 0")
    return {"source": source, "buffer": buffer, "mill_input": mill_input, "mill_output": mill_output}


def callback_witnesses(rcon, rows):
    result = []
    for collected in (row for row in rows if row.get("type") == "PRODUCTION_OUTPUT_COLLECTED"):
        raw = rcon.run("sable mill-process " + collected["job"])
        require("MILL_PROCESS VERIFIED_CALLBACK" in raw and f"citizen={collected['citizen']}" in raw,
                "Native callback journal disagrees with service output")
        for source, event in (("wheatBefore", "wheat_before"), ("wheatAfter", "wheat_after"),
                              ("flourBefore", "flour_before"), ("flourAfter", "flour_after"),
                              ("startTick", "processing_start_tick"), ("tick", "process_tick")):
            match = re.search(r"\b" + source + r"=(\d+)\b", raw)
            require(match and int(match.group(1)) == collected[event], "Native callback field differs: " + source)
        result.append({"job": collected["job"], "native_response": raw})
    for owner in {row["citizen"] for row in rows if row.get("type") == "PRODUCTION_SETTLED"}:
        raw = rcon.run(f'data get entity {owner} ForgeData."hearthbound.millExperiment".phase')
        require('"FINALIZED"' in raw, "Completed actor trace remains eligible for another mill job")
    return result


def private_models(current):
    citizens = current.get("citizens")
    require(isinstance(citizens, list) and len(citizens) == 2, "Missing both citizen snapshots")
    result = {}
    for citizen in citizens:
        require(citizen.get("loaded") is True, "A citizen is not loaded for restart verification")
        require(citizen.get("learning_digest"), "Missing private learning replay digest")
        result[citizen["citizen"]] = citizen["learning_digest"]
    require(len(result) == 2, "Duplicate citizen identity")
    return result


def run_live(rcon, result):
    result["before"] = setup(rcon)
    require(result["before"]["source"]["items"] == {"minecraft:wheat": INITIAL}
            and not result["before"]["buffer"]["items"], "Initial inventories differ")
    rcon.require(COMMAND + " start", "NEED_SERVICES_OK")
    deadline = time.monotonic() + DEADLINE_SECONDS
    while True:
        current = status(rcon)
        require(current["held"] == 0, "A live productive service became unresolved")
        if current["output_units"] >= TARGET and current["active_commitments"] == 0:
            break
        require(time.monotonic() < deadline, "Declared production deadline elapsed")
        time.sleep(.5)
    require(current["production_jobs"] >= 2, "One batch is not machine reuse")
    fixed = (current["assigned"], current["transfers"], current["production_jobs"], current["output_units"])
    end = time.monotonic() + CLOSURE_GRACE_SECONDS + QUIET_SECONDS
    quiet_start = end - QUIET_SECONDS
    quiet_sequence = None
    while time.monotonic() < end:
        time.sleep(.5)
        current = status(rcon)
        require(current["held"] == 0 and current["active_commitments"] == 0, "Target closure retained work")
        require((current["assigned"], current["transfers"], current["production_jobs"], current["output_units"]) == fixed,
                "New material work occurred after target satisfaction")
        if quiet_sequence is None and time.monotonic() >= quiet_start:
            quiet_sequence = current["records_total"]
    natural_rows = records(rcon, current["records_total"])
    require(not any(row.get("type") == "OPTION_STARTED" and row.get("option") in ("SUPPLY_WHEAT", "CARRY_REQUEST")
                    for row in natural_rows[quiet_sequence:]), "Communication/service activity did not withdraw")
    result["natural_closure"] = {"grace_seconds": CLOSURE_GRACE_SECONDS, "quiet_seconds": QUIET_SECONDS,
                                  "new_physical_jobs": 0, "new_supply_or_carry_options_in_quiet_window": 0,
                                  "learned_withdrawal_claimed": False}
    rcon.require(COMMAND + " stop", "NEED_SERVICES_OK")
    terminal = status(rcon)
    require(not terminal["enabled"] and terminal["held"] == terminal["active_commitments"] == 0,
            "Completed production did not stop cleanly")
    rows = records(rcon, terminal["records_total"])
    chain = validate_production_chain(rows)
    require(chain["production_jobs"] == terminal["production_jobs"] == terminal["production_credits"],
            "Production ledger and private learning counts differ")
    require(chain["output_items"]["create:wheat_flour"] == terminal["output_units"], "Output count differs")
    result.update(records=rows, chain=chain, terminal=terminal, private_models=private_models(terminal),
                  after=output_witnesses(rcon, chain["production_jobs"], chain["output_items"]),
                  callbacks=callback_witnesses(rcon, rows),
                  status="passed_live_production")
    rcon.require("save-all flush", "Saved the game")
    print("PRODUCTION_SERVICE_LIVE_PASS " + json.dumps(chain, sort_keys=True), flush=True)


def verify_restart_and_hold(rcon, result):
    require(result.get("status") == "passed_live_production", "No completed first phase")
    current = status(rcon)
    require(not current["enabled"] and current["held"] == current["active_commitments"] == 0,
            "Completed restart resumed or held finished work")
    require(private_models(current) == result["private_models"], "Private model changed on clean replay")
    require(records(rcon, len(result["records"])) == result["records"], "Completed provenance changed on restart")
    for key in ("assigned", "transfers", "production_jobs", "output_units", "cost_updates", "production_credits"):
        require(current[key] == result["terminal"][key], "Restart changed completed count: " + key)
    result["clean_restart"] = {"status": current,
        "inventories": output_witnesses(rcon, result["chain"]["production_jobs"], result["chain"]["output_items"])}
    # A separate intervention creates a real unfinished service. No reserved
    # machine inventory is edited: remove only the external power before start.
    rcon.require(f"setblock {xyz(MOTOR)} minecraft:stone replace", "changed")
    rcon.require(f"{COMMAND} set-target {xyz(BUFFER)} {current['output_units'] + 2}", "NEED_SERVICES_OK")
    rcon.require(COMMAND + " start", "NEED_SERVICES_OK")
    deadline = time.monotonic() + DEADLINE_SECONDS
    completed_transfers = current["transfers"]
    while True:
        pending = status(rcon)
        require(pending["production_jobs"] == current["production_jobs"], "Unpowered machine produced credited output")
        if pending["transfers"] == completed_transfers + 1:
            break
        require(pending["transfers"] <= completed_transfers + 1, "Unpowered mill admitted extra inputs")
        require(pending["held"] == 0, "Pending fixture failed before deliberate stop")
        require(time.monotonic() < deadline, "No real pending input before declared deadline")
        time.sleep(.5)
    rcon.require(COMMAND + " stop", "NEED_SERVICES_OK")
    held = status(rcon)
    require(not held["enabled"] and held["held"] == held["active_commitments"] == 1,
            "Stop freed unresolved productive custody")
    mill = inventory(rcon, MILL, "InputInventory.Items", {"minecraft:wheat"})
    require(mill["items"] == {"minecraft:wheat": 1}, "Real pending input was not retained")
    reservation = rcon.run(f"sable mill-reservation {xyz(MILL)}")
    require("MILL_RESERVATION HELD" in reservation, "Pending machine reservation was released")
    result["held_before_restart"] = {"status": held, "models": private_models(held),
        "records": records(rcon, held["records_total"]), "mill_input": mill, "reservation": reservation}
    result["status"] = "passed_clean_restart_and_held_input"
    rcon.require("save-all flush", "Saved the game")
    print("PRODUCTION_SERVICE_CLEAN_RESTART_PASS pending_input_held=true", flush=True)


def verify_held_restart(rcon, result):
    require(result.get("status") == "passed_clean_restart_and_held_input", "No saved pending phase")
    prior = result["held_before_restart"]
    current = status(rcon)
    require(not current["enabled"] and current["held"] == current["active_commitments"] == 1,
            "Unresolved restart lost its held commitment")
    require(private_models(current) == prior["models"], "Unfinished work trained during restart")
    require(records(rcon, len(prior["records"])) == prior["records"], "Held history changed on replay")
    for key in ("assigned", "transfers", "production_jobs", "output_units", "cost_updates", "production_credits"):
        require(current[key] == prior["status"][key], "Held replay changed accounting: " + key)
    rejected = rcon.run(COMMAND + " start")
    require("NEED_SERVICES_DENIED" in rejected, "Start silently released unresolved material")
    time.sleep(QUIET_SECONDS)
    after = status(rcon)
    require(not after["enabled"] and after["held"] == after["active_commitments"] == 1,
            "Held work automatically resumed")
    require(private_models(after) == prior["models"], "Held idle time altered learning")
    source = inventory(rcon, SOURCE, allowed={"minecraft:wheat"})
    mill = inventory(rcon, MILL, "InputInventory.Items", {"minecraft:wheat"})
    output = inventory(rcon, MILL, "OutputInventory.Items")
    buffer = inventory(rcon, BUFFER)
    require(source["items"].get("minecraft:wheat", 0) == INITIAL - result["chain"]["production_jobs"] - 1,
            "Pending restart duplicated or lost source material")
    require(mill["items"] == {"minecraft:wheat": 1} and not output["items"], "Pending physical custody changed")
    require(buffer["items"] == result["chain"]["output_items"], "Pending restart altered delivered production")
    rcon.require(f"sable mill-reservation {xyz(MILL)}", "MILL_RESERVATION HELD")
    result["held_restart"] = {"status": after, "source": source, "mill_input": mill,
                               "mill_output": output, "buffer": buffer, "start_denied": rejected}
    result["status"] = "passed_all_three_phases"
    print("PRODUCTION_SERVICE_FORGE_ACCEPTANCE_PASS repeated_create_production=true "
          "private_online_learning=true recipient_production_provenance=true "
          "clean_restart=true unresolved_restart_held=true learned_occupation_claimed=false", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("live", "restart-and-hold", "held-restart"), required=True)
    parser.add_argument("--output", type=Path, default=Path("run/production-service-acceptance.json"))
    args = parser.parse_args()
    if args.phase == "live":
        result = {"schema": SCHEMA, "status": "running", "origin": "REAL_FORGE_CREATE",
                  "commit": os.environ.get("HEARTHBOUND_EXPECTED_COMMIT", "UNSPECIFIED"),
                  "planned_citizens": 2, "initial_wheat": INITIAL, "target_flour": TARGET,
                  "deadline_seconds_per_active_phase": DEADLINE_SECONDS,
                  "learned_occupation_claimed": False, "causal_improvement_claimed": False}
    else:
        result = json.loads(args.output.read_text())
        require(result.get("schema") == SCHEMA, "Wrong acceptance schema")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with connection(os.environ["HEARTHBOUND_RCON_PASSWORD"]) as rcon:
        try:
            {"live": run_live, "restart-and-hold": verify_restart_and_hold,
             "held-restart": verify_held_restart}[args.phase](rcon, result)
        except Exception as failure:
            result.update(status="failed", failed_phase=args.phase,
                          error=type(failure).__name__ + ": " + str(failure))
            try:
                result["failure_status"] = status(rcon)
                result["failure_records"] = records(rcon, result["failure_status"]["records_total"])
            except Exception as capture_failure:
                result["capture_failure"] = str(capture_failure)
            raise
        finally:
            args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        rcon.stop_server()


if __name__ == "__main__":
    main()
