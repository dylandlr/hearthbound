#!/usr/bin/env python3
"""Witness bounded idle discovery, a real transfer, and clean-restart identity.

The disposable arena contains one citizen, one wheat source beyond the old
near scan, an empty control, and a loaded wheat control outside the arena's
sensing reach. After enable, only read-only probes run until terminal disable.
"""
import argparse
import gzip
import json
import math
from pathlib import Path
import re
import time
from uuid import UUID

from rcon_neural_report_haul import Rcon
from rcon_colony_completion_boundary import (
    ColonyNbtReader, fields, inventory, packed_position, parse_trace,
    saved_uuid, state, tested_commit, validate_state,
)

WORLD = Path("run/colony-bounded-discovery-world")
BEFORE = Path("colony-bounded-discovery-before.json")
SOURCE = "2 101 8"
EMPTY = "1 101 6"
DESTINATION = "10 101 8"
FAR = "40 101 8"
SABLE = "@e[type=minecraft:villager,name=Sable,limit=1]"
MARKER = "COLONY_DISCOVERY_V0_12 "
SCHEMA = "hearthbound.colony-discovery.v1"
DIMENSION = "minecraft:overworld"
POSITION_BUDGET = 75
INSPECTION_BUDGET = 4
WINDOW_SECONDS = 150
ORIGINAL_CITIZEN = None


def xyz(position):
    return list(map(int, position.split()))


def canonical_uuid(value):
    assert isinstance(value, str) and str(UUID(value)) == value, value
    return value


def read_saved_data(name):
    payload = gzip.decompress((WORLD / "data" / name).read_bytes())
    assert len(payload) <= 1024 * 1024, "Unexpected oversized fixture SavedData"
    return ColonyNbtReader(payload).root()["data"]


def wait_for_original(rcon, citizen, timeout=30):
    """Readiness probes never create, move, or replace the expected actor."""
    if citizen != SABLE:
        canonical_uuid(citizen)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = rcon.run(f"execute if entity {citizen}").strip()
        if response == "Test passed, count: 1" and time.monotonic() < deadline:
            return
        time.sleep(0.25)
    raise AssertionError("Original fixture citizen did not load within readiness window")


def original_citizen(rcon):
    wait_for_original(rcon, SABLE)
    response = rcon.require(f"data get entity {SABLE} UUID", "entity data:")
    match = re.search(r"\[I;\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\]", response)
    assert match, response
    return canonical_uuid(saved_uuid([int(part) for part in match.groups()]))


def audit_page(rcon, citizen, offset=0):
    response = rcon.require(f"hearthbound-colony discovery-audit {citizen} {offset}", MARKER)
    result = json.loads(response.split(MARKER, 1)[1].strip())
    assert result["schema"] == SCHEMA and result["citizen"] == citizen, result
    assert result["offset"] == offset, result
    return result


def collect_audit(rcon, citizen):
    """Call after disable for a stable, bounded, complete citizen snapshot."""
    first = audit_page(rcon, citizen)
    observations = list(first["observations"])
    next_offset = first["next_offset"]
    seen_offsets = {0}
    metadata = {k: v for k, v in first.items()
                if k not in ("observations", "offset", "next_offset")}
    while next_offset is not None:
        assert type(next_offset) is int and next_offset > 0, first
        assert next_offset not in seen_offsets and len(seen_offsets) < 64, first
        seen_offsets.add(next_offset)
        page = audit_page(rcon, citizen, next_offset)
        assert {k: v for k, v in page.items()
                if k not in ("observations", "offset", "next_offset")} == metadata, \
            "Discovery changed during disabled audit"
        observations.extend(page["observations"])
        next_offset = page["next_offset"]
    assert len(observations) == first["observation_total"], first
    return dict(metadata, observations=observations)


def outside_near_scan(source, observer):
    block = [math.floor(value) for value in observer]
    return not (abs(source[0] - block[0]) <= 2
                and abs(source[1] - block[1]) <= 1
                and abs(source[2] - block[2]) <= 2)


def validate_audit(audit, citizen, world=None):
    """Reject testimony with invalid geometry, identity, budgets or semantics."""
    canonical_uuid(citizen)
    assert audit["schema"] == SCHEMA and audit["citizen"] == citizen, audit
    assert audit["dimension"] == DIMENSION, audit
    assert audit["read_only"] is True and audit["retained"] is True, audit
    assert audit["scope"] == "SESSION_LOCAL_INCREMENTAL_FALLBACK", audit
    assert audit["counter_scope"] == "RETAINED_CITIZEN_CURSOR_LIFETIME", audit
    assert audit["citizen_evictions"] == audit["observation_evictions"] == 0, audit
    assert audit["retained_citizens"] == 1, audit
    canonical_uuid(audit["world"])
    canonical_uuid(audit["episode"])
    if world is not None:
        assert audit["world"] == world, audit
    bounds = audit["bounds"]
    assert bounds["positions_per_opportunity"] == POSITION_BUDGET, bounds
    assert bounds["inspections_per_opportunity"] == INSPECTION_BUDGET, bounds
    assert bounds["cadence_ticks"] == 20, bounds
    assert bounds["citizens"] == 256 and bounds["observations"] == 128, bounds
    assert bounds["page_size"] == 2, bounds
    stats = audit["stats"]
    for key in ("opportunities", "probes", "inspections", "proposals",
                "max_cycle_probes", "max_cycle_inspections", "last_tick", "cursor", "cycles"):
        assert type(stats[key]) is int and stats[key] >= 0, (key, stats)
    assert stats["opportunities"] > 0 and stats["inspections"] > 0, stats
    assert 0 < stats["max_cycle_probes"] <= POSITION_BUDGET, stats
    assert 0 < stats["max_cycle_inspections"] <= INSPECTION_BUDGET, stats
    assert stats["probes"] <= stats["opportunities"] * POSITION_BUDGET, stats
    assert stats["inspections"] <= stats["opportunities"] * INSPECTION_BUDGET, stats
    assert stats["proposals"] <= stats["inspections"] <= stats["probes"], stats
    observations = audit["observations"]
    assert len(observations) == audit["observation_total"] <= bounds["observations"], audit
    assert len(observations) == stats["inspections"] == audit["retained_observations"], audit
    sequences = []
    for entry in observations:
        assert entry["citizen"] == citizen and entry["world"] == audit["world"], entry
        assert entry["episode"] == audit["episode"] and entry["dimension"] == DIMENSION, entry
        assert entry["origin"] == "BOUNDED_IDLE_DISCOVERY", entry
        assert type(entry["sequence"]) is int and entry["sequence"] >= 0, entry
        assert type(entry["tick"]) is int and 0 <= entry["tick"] <= stats["last_tick"], entry
        sequences.append(entry["sequence"])
        source, observer = entry["source"], entry["observer"]
        assert entry["destination"] == xyz(DESTINATION), entry
        assert len(source) == len(observer) == 3, entry
        assert all(type(value) is int for value in source), entry
        assert all(type(value) in (int, float) and math.isfinite(value) for value in observer), entry
        # The closed arena guarantees the distant loaded control stays out of range.
        assert 1 <= observer[0] < 16 and 101 <= observer[1] < 104 and 5 <= observer[2] < 12, entry
        measured = sum((center + 0.5 - position) ** 2 for center, position in zip(source, observer))
        assert type(entry["distance_squared"]) in (int, float), entry
        assert math.isfinite(entry["distance_squared"]), entry
        assert math.isclose(measured, entry["distance_squared"], rel_tol=1e-9, abs_tol=1e-6), entry
        assert measured <= 16 * 16, entry
        assert abs(source[1] - math.floor(observer[1])) <= 1, entry
        assert outside_near_scan(source, observer), "Fallback inspected the current near cube"
        assert source != xyz(FAR), "Out-of-range control appeared in citizen observations"
        assert type(entry["wheat"]) is int and entry["wheat"] >= 0, entry
        if entry["state"] == "AVAILABLE":
            assert entry["wheat"] > 0 and entry["reason"] == "OBSERVED", entry
            assert entry["proposal"] in ("CREATED", "EXISTING", "CAPACITY_DENIED"), entry
            if entry["proposal"] != "CAPACITY_DENIED":
                assert type(entry["task_id"]) is int and entry["task_id"] > 0, entry
            else:
                assert entry["task_id"] is None, entry
        else:
            assert entry["state"] in ("EMPTY", "UNKNOWN") and entry["wheat"] == 0, entry
            assert entry["proposal"] == "NONE" and entry["task_id"] is None, entry
            if entry["state"] == "EMPTY":
                assert entry["reason"] == "OBSERVED", entry
    assert sequences == sorted(set(sequences)), "Duplicate or reordered discovery observations"
    available = [entry for entry in observations
                 if entry["source"] == xyz(SOURCE) and entry["state"] == "AVAILABLE"
                 and entry["wheat"] == 1 and entry["proposal"] == "CREATED"
                 and outside_near_scan(entry["source"], entry["observer"])]
    empty = [entry for entry in observations
             if entry["source"] == xyz(EMPTY) and entry["state"] == "EMPTY"
             and entry["proposal"] == "NONE" and entry["task_id"] is None]
    assert len(available) == 1, "No unique outer observation created the actual source task"
    assert empty, "Empty control was not actually observed by bounded discovery"
    return available[0], empty[0]


def validate_saved(saved, trace):
    assert len(saved["tasks"]) == len(saved["decisionHistory"]) == 1, saved
    assert saved["historyDeniedCapacity"] == 0, saved
    assert saved["destination"] == packed_position(DESTINATION), saved
    task, record = saved["tasks"][0], saved["decisionHistory"][0]
    assert task["id"] == record["task"] == trace["task"], saved
    assert task["state"] == "DONE" and record["status"] == "PHYSICALLY_COMPLETED", saved
    assert task["dimension"] == DIMENSION, saved
    assert saved_uuid(task["owner"]) == saved_uuid(record["citizen"]) == trace["citizen"]
    assert saved_uuid(task["job"]) == saved_uuid(record["job"]) == trace["job"]
    assert task["assignedTick"] == record["assigned"] == trace["assigned"]
    for key, position in (("source", SOURCE), ("destination", DESTINATION)):
        assert task[key] == record[key] == packed_position(position), saved
    for key in ("observed", "decided", "delivered", "revision"):
        assert record[key] == trace[key], saved
    for key in ("decision", "evidence", "episode"):
        assert saved_uuid(record[key]) == trace[key], saved


def validate_result(result):
    assert result["schema"] == "hearthbound.colony-bounded-discovery.v1", result
    assert re.fullmatch(r"[0-9a-f]{40}", result["tested_commit"]), result
    citizen = canonical_uuid(result["citizen"])
    world = canonical_uuid(result["world"])
    witness, empty = validate_audit(result["discovery"], citizen, world)
    trace = result["trace"]
    for key in ("citizen", "job", "decision", "evidence", "episode"):
        canonical_uuid(trace[key])
    assert trace["citizen"] == citizen and trace["episode"] == witness["episode"], result
    assert trace["task"] == witness["task_id"], result
    assert witness["tick"] <= trace["observed"] <= trace["decided"] <= trace["assigned"] <= trace["delivered"], result
    assert trace["assigned"] - trace["observed"] <= 20 and trace["revision"] > 0, result
    assert result["motor"]["job"] == trace["job"] and result["motor"]["phase"] == 2, result
    assert result["inventories_before"] == {"source": 1, "empty": 0, "destination": 0, "far": 1}, result
    assert result["inventories_after"] == {"source": 0, "empty": 0, "destination": 1, "far": 1}, result
    assert result["far_memory_status"] == "UNKNOWN", result
    assert type(result["witness_seconds"]) in (int, float), result
    assert math.isfinite(result["witness_seconds"]) and 0 <= result["witness_seconds"] < WINDOW_SECONDS, result
    assert result["behavioral_retries"] == 0 and result["active_interventions_after_enable"] == 0, result
    assert result["learning_authorized"] is False and result["reward_authorized"] is False, result
    validate_state(result["final"], 1)
    validate_saved(result["persisted"], trace)
    return witness, empty


def motor(rcon, citizen):
    response = rcon.require(f"execute at {citizen} run sable haul-audit", "AUDIT job=")
    values = fields(response, "AUDIT ")
    return {"job": canonical_uuid(values["job"]), "phase": int(values["phase"]), "audit": response}


def check_inventories(rcon, delivered):
    for position, amount in ((SOURCE, 1 - delivered), (EMPTY, 0),
                             (DESTINATION, delivered), (FAR, 1)):
        inventory(rcon, position, amount)
    return {"source": 1 - delivered, "empty": 0, "destination": delivered, "far": 1}


def far_memory(rcon, citizen):
    response = rcon.require(f"hearthbound citizen_memory {FAR} {citizen}", "CITIZEN_KNOWLEDGE ")
    values = fields(response, "CITIZEN_KNOWLEDGE ")
    assert values["citizen"] == citizen and values["source"] == f"{DIMENSION}|40,101,8", response
    assert values["status"] == "UNKNOWN" and values["action_authorized"] == "false", response
    return values["status"]


def before_restart():
    global ORIGINAL_CITIZEN
    commit = tested_commit()
    with Rcon() as rcon:
        for command in (
            "gamerule doMobSpawning false", "forceload add 0 0 47 15",
            "fill 0 100 4 16 105 12 minecraft:air",
            "fill 0 100 4 16 100 12 minecraft:stone",
            "fill 0 101 4 0 104 12 minecraft:stone",
            "fill 16 101 4 16 104 12 minecraft:stone",
            "fill 0 101 4 16 104 4 minecraft:stone",
            "fill 0 101 12 16 104 12 minecraft:stone",
            "fill 0 104 4 16 104 12 minecraft:stone",
            f'setblock {SOURCE} minecraft:chest{{Items:[{{Slot:0b,id:"minecraft:wheat",Count:1b}}]}} replace',
            f"setblock {EMPTY} minecraft:chest replace",
            f"setblock {DESTINATION} minecraft:chest replace",
            "setblock 40 100 8 minecraft:stone replace",
            f'setblock {FAR} minecraft:chest{{Items:[{{Slot:0b,id:"minecraft:wheat",Count:1b}}]}} replace',
        ):
            rcon.run(command)
        rcon.require("execute positioned 12.5 101 8.5 run sable spawn", "Sable spawned")
        citizen = original_citizen(rcon)
        ORIGINAL_CITIZEN = citizen
        rcon.require(f"hearthbound-colony set-destination {DESTINATION}", "Registered shared destination")
        validate_state(state(rcon), 0)
        initial = audit_page(rcon, citizen)
        assert initial["retained"] is False and initial["observation_total"] == 0, initial
        inventories_before = check_inventories(rcon, 0)
        far_memory(rcon, citizen)
        rcon.require("hearthbound-colony enable", "dispatch enabled")
        start = time.monotonic()
        deadline = start + WINDOW_SECONDS
        # The enabled interval has no writes to citizens, tasks, or inventories.
        # Source and empty witnesses must be real records, never inferred from setup.
        found_witnesses = False
        while time.monotonic() < deadline:
            time.sleep(1)
            current = fields(rcon.require("hearthbound-colony audit", "COLONY_V1 "), "COLONY_V1 ")
            assert int(current["held"]) == 0 and int(current["done"]) <= 1, current
            if int(current["done"]) != 1:
                continue
            first = audit_page(rcon, citizen)
            # Only a few actual inventories exist in this fixture. Collect the
            # current pages for witness detection; final validation is disabled/stable.
            seen = list(first["observations"])
            offset = first["next_offset"]
            visits = 0
            while offset is not None:
                assert visits < 64, "Unbounded discovery pagination"
                page = audit_page(rcon, citizen, offset)
                seen.extend(page["observations"])
                offset = page["next_offset"]
                visits += 1
            found_source = any(entry["source"] == xyz(SOURCE)
                               and entry["state"] == "AVAILABLE"
                               and entry["proposal"] == "CREATED"
                               and outside_near_scan(entry["source"], entry["observer"])
                               for entry in seen)
            found_empty = any(entry["source"] == xyz(EMPTY) and entry["state"] == "EMPTY"
                              for entry in seen)
            if found_source and found_empty:
                accepted_at = time.monotonic()
                assert accepted_at < deadline, "Discovery witnesses arrived after fixed acceptance window"
                witness_seconds = accepted_at - start
                found_witnesses = True
                break
        assert found_witnesses, "No verified outer-source delivery and observed empty control within fixed window"
        rcon.require("hearthbound-colony disable", "Dispatch disabled")
        audit = collect_audit(rcon, citizen)
        final = state(rcon)
        validate_state(final, 1)
        actual_motor = motor(rcon, citizen)
        trace = parse_trace(rcon.require("hearthbound-colony decision-traces", "COLONY_TRACES_V0_4 "),
                            actual_motor["job"])
        inventories_after = check_inventories(rcon, 1)
        memory_status = far_memory(rcon, citizen)
        rcon.require("save-all flush", "Saved the game")
        persisted = read_saved_data("hearthbound_colony_tasks_v1.dat")
        world = canonical_uuid(read_saved_data("hearthbound_world_identity_v1.dat")["worldUuid"])
        result = {"schema": "hearthbound.colony-bounded-discovery.v1", "tested_commit": commit,
                  "world": world, "citizen": citizen, "discovery": audit, "trace": trace,
                  "motor": actual_motor, "final": final, "persisted": persisted,
                  "inventories_before": inventories_before, "inventories_after": inventories_after,
                  "far_memory_status": memory_status, "behavioral_retries": 0,
                  "active_interventions_after_enable": 0,
                  "learning_authorized": False, "reward_authorized": False,
                  "witness_seconds": witness_seconds,
                  "elapsed_seconds": round(time.monotonic() - start, 3),
                  "full_world_reliability_replicate": False,
                  "communication_benefit_established": False}
        validate_result(result)
        BEFORE.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print("COLONY_BOUNDED_DISCOVERY_PASS outer_source=1 empty_observed=1 physical_deliveries=1 "
              "far_source_unchanged=true original_citizen=true reward_authorized=false", flush=True)
        rcon.run("stop")


def after_restart():
    global ORIGINAL_CITIZEN
    prior = json.loads(BEFORE.read_text())
    validate_result(prior)
    ORIGINAL_CITIZEN = prior["citizen"]
    assert prior["tested_commit"] == tested_commit()
    with Rcon() as rcon:
        wait_for_original(rcon, prior["citizen"])
        current = state(rcon)
        validate_state(current, 1)
        assert current == prior["final"], "Restart changed completed task or history counts"
        assert check_inventories(rcon, 1) == prior["inventories_after"]
        far_memory(rcon, prior["citizen"])
        current_motor = motor(rcon, prior["citizen"])
        assert current_motor["job"] == prior["trace"]["job"] and current_motor["phase"] == 2
        audit = audit_page(rcon, prior["citizen"])
        assert audit["retained"] is False and audit["observation_total"] == 0, audit
        assert audit["world"] == prior["world"] and audit["episode"] != prior["discovery"]["episode"], audit
        time.sleep(2.2)
        assert state(rcon) == current, "Disabled restart duplicated a job or completion"
        rcon.require("save-all flush", "Saved the game")
        persisted = read_saved_data("hearthbound_colony_tasks_v1.dat")
        validate_saved(persisted, prior["trace"])
        assert persisted == prior["persisted"], "Restart changed persisted job/evidence identity"
        assert read_saved_data("hearthbound_world_identity_v1.dat")["worldUuid"] == prior["world"]
        Path("colony-bounded-discovery-after.json").write_text(json.dumps({
            "schema": "hearthbound.colony-bounded-discovery-restart.v1",
            "tested_commit": prior["tested_commit"], "world": prior["world"],
            "citizen": prior["citizen"], "state": current, "persisted": persisted,
            "discovery_session_reset": True, "dispatch_enabled": False,
            "physical_inventory_preserved": True, "original_job_preserved": True,
            "crash_atomicity_verified": False,
        }, indent=2, sort_keys=True) + "\n")
        print("COLONY_BOUNDED_DISCOVERY_RESTART_PASS original_job=true tasks=1 "
              "history_complete=1 dispatch_disabled=true session_cursor_reset=true", flush=True)
        rcon.run("stop")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    args = parser.parse_args()
    try:
        (before_restart if args.phase == "before" else after_restart)()
    except Exception as error:
        failure = {"schema": "hearthbound.colony-bounded-discovery-failure.v1",
                   "phase": args.phase, "status": "FAILED", "error_type": type(error).__name__,
                   "error": str(error), "behavioral_retries": 0}
        try:
            with Rcon() as diagnostic:
                def capture(name, read):
                    try:
                        failure[name] = read()
                    except Exception as unavailable:
                        failure[name + "_error"] = type(unavailable).__name__ + ": " + str(unavailable)

                capture("state", lambda: state(diagnostic))
                failure["original_citizen"] = ORIGINAL_CITIZEN
                actor = ORIGINAL_CITIZEN or SABLE
                capture("position", lambda: diagnostic.run(f"data get entity {actor} Pos"))
                for label, position in (("source", SOURCE), ("empty", EMPTY),
                                        ("destination", DESTINATION), ("far", FAR)):
                    capture(label, lambda position=position: diagnostic.run(f"data get block {position} Items"))
                capture("discovery_summary", lambda: diagnostic.run("hearthbound-colony discovery-audit"))
                if ORIGINAL_CITIZEN:
                    # Preserve partial, possibly changing live pages as raw
                    # diagnostics; never promote them into a passing snapshot.
                    failure["discovery_pages"] = []
                    offset, seen = 0, set()
                    while offset is not None:
                        assert offset not in seen and len(seen) < 64, "Invalid diagnostic pagination"
                        seen.add(offset)
                        page = audit_page(diagnostic, ORIGINAL_CITIZEN, offset)
                        failure["discovery_pages"].append(page)
                        offset = page["next_offset"]
        except Exception as unavailable:
            failure["diagnostic_error"] = type(unavailable).__name__ + ": " + str(unavailable)
        Path(f"colony-bounded-discovery-{args.phase}-failure.json").write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n")
        raise
