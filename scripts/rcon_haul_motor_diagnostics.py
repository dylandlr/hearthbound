#!/usr/bin/env python3
"""Controlled Forge probes for read-only hauling and chunk-ticking diagnostics.

The operator constructs/removes a barrier and changes one probe chunk ticket.
These interventions are explicit test controls, never citizen actions or rewards.
"""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time
from uuid import UUID

from haul_motor_diagnostics import (
    COMMAND, PREFIX, authority_view, capture_snapshot, command_for, parse_snapshot,
    require, require_blocked_cargo, require_completed,
)
from rcon_obstructed_haul_acceptance import (
    BARRIER, OPEN_BARRIER, MAX_POLLS, POLL_SECONDS, make_corridor,
    counts, inventory_empty, source_owned, source_unclaimed,
)
from rcon_private_communication_trial import connection
from run_colony_reliability_trial import world_evidence

PLAN_SCHEMA = "hearthbound.haul-motor-diagnostics-plan.v1"
RESULT_SCHEMA = "hearthbound.haul-motor-diagnostics-acceptance.v1"
SEED = 43101
LEVEL_NAME = "haul-motor-diagnostics-world"
SOURCE_A, DEST_A, SOURCE_B, DEST_B = (11, 100, 1), (7, 100, 1), (24, 100, 1), (19, 100, 1)
MISSING_CITIZEN = "00000000-0000-4000-8000-000000000217"
PROBE_ANCHOR = (4096, 4096)
PROBE_COLUMN = (4104, 4088)
PROBE_POSITION = (4104.5, 101.0, 4088.5)
PROBE_GAP_TICKS = 40
PROBE_POLL_SECONDS, PROBE_MAX_POLLS = 0.25, 60
PROTOCOL_FILES = (
    "scripts/haul_motor_diagnostics.py", "scripts/rcon_haul_motor_diagnostics.py",
    "scripts/test_haul_motor_diagnostics.py", ".github/workflows/real-haul-motor-diagnostics.yml",
    "scripts/rcon_obstructed_haul_acceptance.py", "scripts/rcon_two_citizen_haul_acceptance.py",
    "scripts/rcon_private_communication_trial.py", "scripts/run_colony_reliability_trial.py",
    "src/main/java/dev/hearthbound/world/HaulMotorDiagnostics.java",
    "src/main/java/dev/hearthbound/world/SableController.java",
    "src/main/java/dev/hearthbound/world/SableHauling.java",
    "src/main/java/dev/hearthbound/world/HaulClaims.java",
    "src/main/java/dev/hearthbound/world/HearthboundWorldIdentity.java",
)


def plan(repo):
    sources = {name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in PROTOCOL_FILES}
    return {"schema": PLAN_SCHEMA, "seed": SEED, "level_name": LEVEL_NAME,
            "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
            "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True).strip(),
            "protocol_sha256": hashlib.sha256(json.dumps(sources, sort_keys=True).encode()).hexdigest(),
            "sources_sha256": sources, "behavioral_retries_allowed": 0,
            "blocked_haul": {"source_A": SOURCE_A, "destination_A": DEST_A,
                             "source_B": SOURCE_B, "destination_B": DEST_B,
                             "source_stock_each": 8, "barrier": BARRIER, "open_barrier": OPEN_BARRIER,
                             "poll_seconds": POLL_SECONDS, "max_polls_per_stage": MAX_POLLS},
            "chunk_probe": {"anchor_column": PROBE_ANCHOR, "probe_column": PROBE_COLUMN,
                            "probe_position": PROBE_POSITION, "no_ai": True, "haul_assigned": False,
                            "setup_forces_both_chunks": True, "remove_probe_ticket_before_measurement": True,
                            "read_gap_game_ticks": PROBE_GAP_TICKS,
                            "poll_seconds": PROBE_POLL_SECONDS, "max_polls_per_stage": PROBE_MAX_POLLS,
                            "resume_intervention": "FORCE_PROBE_CHUNK_ONCE"},
            "operator_interventions_are_agent_actions": False,
            "diagnostics_authorize_reward_or_repair": False,
            "original_reliability_failure_cause_established": False}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n")


def native_uuid(response):
    values = re.findall(r"\[I;\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\]", response)
    require(len(values) == 1, "Native entity UUID is absent or ambiguous")
    return str(UUID(bytes=struct.pack(">iiii", *map(int, values[0]))))


def spawn_citizen(rcon, position):
    x, y, z = position
    rcon.require(f"execute positioned {x} {y} {z} run sable spawn", "Sable spawned")
    response = rcon.require(f"execute positioned {x} {y} {z} run data get entity "
                            "@e[type=minecraft:villager,name=Sable,sort=nearest,limit=1] UUID", "entity data:")
    return native_uuid(response)


def native_haul(rcon, citizen):
    return rcon.require(f'data get entity {citizen} ForgeData."hearthbound.haul"', "entity data:")


def native_inventories(rcon):
    return {name: rcon.require(f"data get block {p[0]} {p[1]} {p[2]} Items", "block data:")
            for name, p in (("source_A", SOURCE_A), ("destination_A", DEST_A),
                            ("source_B", SOURCE_B), ("destination_B", DEST_B))}


def snapshot(rcon, data, citizen, label):
    value = capture_snapshot(rcon, citizen, expected_dimension="minecraft:overworld")
    data.setdefault("snapshots", []).append({"label": label, "snapshot": value})
    return value


def wait_probe(rcon, data, citizen, predicate, label, sleep):
    for index in range(PROBE_MAX_POLLS):
        value = snapshot(rcon, data, citizen, f"{label}-{index}")
        if predicate(value):
            return value
        sleep(PROBE_POLL_SECONDS)
    raise AssertionError("Chunk diagnostic did not reach declared condition: " + label)


def run_chunk_probe(rcon, data, sleep=time.sleep):
    """Change chunk tickets only for a fresh, unassigned, stationary test citizen."""
    rcon.require(f"forceload add {PROBE_ANCHOR[0]} {PROBE_ANCHOR[1]}", "force loaded")
    rcon.require(f"forceload add {PROBE_COLUMN[0]} {PROBE_COLUMN[1]}", "force loaded")
    for command in (
        "fill 4102 100 4086 4106 104 4090 minecraft:stone",
        "fill 4103 101 4087 4105 103 4089 minecraft:air",
    ):
        rcon.require(command, "filled")
    citizen = spawn_citizen(rcon, PROBE_POSITION)
    data["probe_citizen"] = citizen
    rcon.require(f"data merge entity {citizen} {{NoAI:1b}}", "modified")
    initial = snapshot(rcon, data, citizen, "chunk-probe-initial-forced")
    require(initial["status"] == "OBSERVED" and initial["entity"]["no_ai"] is True
            and initial["entity"]["forced_chunk"] is True and initial["haul"]["present"] is False,
            "Fresh chunk probe was not stationary, forced, and unassigned")
    rcon.require(f"forceload remove {PROBE_COLUMN[0]} {PROBE_COLUMN[1]}", "force loaded")
    suspended = wait_probe(rcon, data, citizen,
        lambda s: s["status"] == "OBSERVED" and s["entity"]["position_entity_ticking"] is False
        and s["entity"]["forced_chunk"] is False, "chunk-probe-suspend", sleep)
    reads = [suspended]
    for index in range(2):
        previous = reads[-1]
        value = wait_probe(rcon, data, citizen,
            lambda s: s["status"] == "OBSERVED" and s["tick"] - previous["tick"] >= PROBE_GAP_TICKS,
            f"chunk-probe-suspended-gap-{index}", sleep)
        require(value["entity"]["chunk_loaded"] is True
                and value["entity"]["position_entity_ticking"] is False
                and value["entity"]["forced_chunk"] is False
                and value["entity"]["tick_count"] == suspended["entity"]["tick_count"]
                and value["entity"]["position"] == suspended["entity"]["position"]
                and value["entity"]["no_ai"] is True and value["haul"]["present"] is False,
                "Probe was not loaded with stable entity ticks during advancing world time")
        reads.append(value)
    data["chunk_suspended_reads"] = reads
    rcon.require(f"forceload add {PROBE_COLUMN[0]} {PROBE_COLUMN[1]}", "force loaded")
    resumed = wait_probe(rcon, data, citizen,
        lambda s: s["status"] == "OBSERVED" and s["entity"]["position_entity_ticking"] is True
        and s["entity"]["forced_chunk"] is True
        and s["entity"]["tick_count"] > suspended["entity"]["tick_count"], "chunk-probe-resume", sleep)
    require(resumed["entity"]["no_ai"] is True and resumed["haul"]["present"] is False,
            "Chunk probe changed action state")
    data["chunk_resumed"] = resumed


def run_fixture(rcon, data, sleep=time.sleep):
    data["phase"] = "SETUP"
    make_corridor(rcon)
    a = spawn_citizen(rcon, (12, 100, 1))
    b = spawn_citizen(rcon, (22, 100, 1))
    require(a != b, "Fixture resolved the same citizen twice")
    data["citizens"] = {"A": a, "B": b}
    data["native_inventories_before"] = native_inventories(rcon)
    for citizen, source, destination in ((a, SOURCE_A, DEST_A), (b, SOURCE_B, DEST_B)):
        command = f"execute as {citizen} at @s run sable haul " + " ".join(map(str, (*source, *destination)))
        rcon.require(command, "Sable assigned wheat haul")
    data["phase"] = "WAITING_FOR_BLOCKED_CARGO_AND_B_DELIVERY"
    blocked = complete_b = None
    for index in range(MAX_POLLS):
        sleep(POLL_SECONDS)
        current_a = snapshot(rcon, data, a, f"preopen-A-{index}")
        current_b = snapshot(rcon, data, b, f"preopen-B-{index}")
        if (current_a["status"] == "OBSERVED" and current_a["haul"]["phase"] == 1
                and current_a["haul"]["cargo"].get("count") == 1):
            blocked = current_a
        if current_b["status"] == "OBSERVED" and current_b["haul"]["phase"] == 2:
            complete_b = current_b
        if blocked is not None and complete_b is not None:
            break
    require(blocked is not None and complete_b is not None,
            "Blocked A did not acquire cargo or independent B did not finish")
    job_a = require_blocked_cargo(blocked, a, SOURCE_A, DEST_A)
    job_b = complete_b["haul"]["job"]
    require_completed(complete_b, b, job_b, SOURCE_B, DEST_B)
    data["jobs"] = {"A": job_a, "B": job_b}
    sleep(POLL_SECONDS)
    data["phase"] = "READ_ONLY_BLOCKED_INSPECTION"
    native_before = native_haul(rcon, a)
    first = snapshot(rcon, data, a, "blocked-repeat-first")
    repeat = snapshot(rcon, data, a, "blocked-repeat-second")
    native_after = native_haul(rcon, a)
    require_blocked_cargo(first, a, SOURCE_A, DEST_A)
    require_blocked_cargo(repeat, a, SOURCE_A, DEST_A)
    require(authority_view(first) == authority_view(repeat), "Repeated read changed blocked job authority/inventory")
    require(native_before == native_after, "Native blocked haul NBT changed across diagnostic inspection")
    data["blocked_native_haul_before"] = native_before
    data["blocked_native_haul_after"] = native_after
    data["blocked_snapshots"] = [first, repeat]
    counts(rcon, 11, 11, 7, 7)
    inventory_empty(rcon, 7)
    counts(rcon, 24, 19, 7, 1)
    source_owned(rcon, 11)
    source_unclaimed(rcon, 24)
    rcon.require("hearthboundclaims count", "Active source claims in this dimension: 1")
    rcon.require("execute if block 9 100 1 minecraft:stone", "test passed")
    data["native_inventories_blocked"] = native_inventories(rcon)
    data["phase"] = "UNBLOCKED_RECOVERY"
    rcon.require(OPEN_BARRIER, "filled")
    rcon.require("execute if block 9 100 1 minecraft:air", "test passed")
    recovered = None
    for index in range(MAX_POLLS):
        sleep(POLL_SECONDS)
        value = snapshot(rcon, data, a, f"postopen-A-{index}")
        if value["status"] == "OBSERVED" and value["haul"]["phase"] == 2:
            recovered = value
            break
    require(recovered is not None, "A did not complete after removing the barrier")
    require_completed(recovered, a, job_a, SOURCE_A, DEST_A)
    require_completed(snapshot(rcon, data, b, "completed-B"), b, job_b, SOURCE_B, DEST_B)
    counts(rcon, 11, 7, 7, 1)
    counts(rcon, 24, 19, 7, 1)
    source_unclaimed(rcon, 11)
    source_unclaimed(rcon, 24)
    rcon.require("hearthboundclaims count", "Active source claims in this dimension: 0")
    data["native_inventories_after"] = native_inventories(rcon)
    data["native_completed_haul"] = {"A": native_haul(rcon, a), "B": native_haul(rcon, b)}
    data["recovered"] = recovered
    data["phase"] = "NEGATIVE_IDENTITY_PROBES"
    missing = snapshot(rcon, data, MISSING_CITIZEN, "missing-citizen")
    require(missing["status"] == "NOT_LOADED_IN_DIMENSION", "Missing UUID silently selected another citizen")
    invalid = parse_snapshot(rcon.run(COMMAND + " invalid-uuid"))
    require(invalid["status"] == "INVALID_UUID", "Invalid UUID was not explicitly rejected")
    data["invalid_uuid_response"] = invalid
    rcon.require('summon minecraft:villager 30 100 1 {CustomName:\'{"text":"UnmarkedProbe"}\',NoAI:1b}',
                 "Summoned new")
    foreign = native_uuid(rcon.require("data get entity @e[type=minecraft:villager,name=UnmarkedProbe,limit=1] UUID",
                                      "entity data:"))
    foreign_result = snapshot(rcon, data, foreign, "unmarked-villager")
    require(foreign_result["status"] == "NOT_A_MARKED_VILLAGER", "Unmarked villager entered worker diagnostics")
    data["phase"] = "CONTROLLED_CHUNK_TICKING_PROBE"
    run_chunk_probe(rcon, data, sleep)
    data["phase"] = "FINISHED"
    data["physical_deliveries"] = 2
    data["wheat_conserved"] = True
    data["blocked_authority_stable_across_reads"] = True
    data["loaded_chunk_suspension_and_resume_observed"] = True
    data["original_reliability_failure_cause_established"] = False
    print("HAUL_MOTOR_DIAGNOSTICS_ACCEPTANCE_PASS blocked_cargo=true repeated_reads_stable=true "
          "physical_deliveries=2 claims=0 loaded_non_ticking_probe=true resumed_ticks=true", flush=True)


def live(output):
    repo = Path(__file__).resolve().parents[1]
    declared = json.loads((output / "planned-trial.json").read_text())
    require(declared == json.loads(json.dumps(plan(repo))), "Checked-out protocol differs from predeclared plan")
    result = {"schema": RESULT_SCHEMA, "source_commit": declared["source_commit"],
              "source_tree": declared["source_tree"], "protocol_sha256": declared["protocol_sha256"],
              "github_run_id": os.environ.get("GITHUB_RUN_ID"),
              "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
              "status": "RUNNING", "fixture_passed": False, "clean_server_exit": False,
              "behavioral_retries": 0, "fixture": {}, "world": None,
              "error": None, "error_type": None, "secondary_errors": []}
    result_path = output / "trial-result.json"
    require(not result_path.exists(), "Refusing to replace an earlier live attempt")
    write_json(result_path, result)
    try:
        with connection(os.environ["HEARTHBOUND_RCON_PASSWORD"]) as rcon:
            try:
                run_fixture(rcon, result["fixture"])
                result["fixture_passed"] = True
                result["status"] = "AWAITING_CLEAN_SHUTDOWN"
            except Exception as error:
                result.update(status="FIXTURE_FAILURE", error_type=type(error).__name__, error=str(error))
                for name, citizen in result["fixture"].get("citizens", {}).items():
                    try:
                        snapshot(rcon, result["fixture"], citizen, "failure-final-" + name)
                    except Exception as diagnostic_error:
                        result["secondary_errors"].append("Diagnostic: " + str(diagnostic_error))
            finally:
                try:
                    rcon.require("save-all flush", "Saved the game")
                except Exception as error:
                    result["secondary_errors"].append("Save: " + str(error))
                try:
                    rcon.stop_server()
                except Exception as error:
                    result["secondary_errors"].append("Stop: " + str(error))
    except Exception as error:
        if result["error"] is None:
            result.update(status="INFRASTRUCTURE_FAILURE", error_type=type(error).__name__, error=str(error))
        else:
            result["secondary_errors"].append("Connection cleanup: " + str(error))
    write_json(result_path, result)
    return 0 if result["fixture_passed"] and not result["secondary_errors"] else 1


def finish(output, server_exit):
    repo = Path(__file__).resolve().parents[1]
    path = output / "trial-result.json"
    result = json.loads(path.read_text())
    result["server_exit_code"] = server_exit
    result["clean_server_exit"] = server_exit == 0
    try:
        world_dir = repo / "run" / LEVEL_NAME
        result["world"] = world_evidence(world_dir, LEVEL_NAME, SEED)
        snapshots = result["fixture"].get("snapshots", [])
        require(all(row["snapshot"]["world"] == result["world"]["world_uuid"] for row in snapshots),
                "Runtime diagnostic world differs from saved world")
        metadata = output / "world-metadata"
        metadata.mkdir(exist_ok=True)
        for source, target in ((world_dir / "level.dat", "level.dat"),
                               (world_dir / "data/hearthbound_world_identity_v1.dat",
                                "hearthbound_world_identity_v1.dat")):
            shutil.copy2(source, metadata / target)
    except Exception as error:
        result["secondary_errors"].append("Saved world evidence: " + str(error))
    if result["fixture_passed"] and result["clean_server_exit"] and not result["secondary_errors"]:
        result["status"] = "PASS"
    elif result["error"] is None:
        result.update(status="EVIDENCE_FAILURE", error="Clean shutdown or saved-world verification failed")
    write_json(path, result)
    ledger = {str(p.relative_to(output)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in output.rglob("*") if p.is_file() and p.name != "evidence-sha256.json"}
    write_json(output / "evidence-sha256.json", {"files": ledger})
    print(json.dumps({key: result[key] for key in ("status", "fixture_passed", "clean_server_exit", "error",
                                                 "secondary_errors")}, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("haul-motor-diagnostics"))
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write-plan", action="store_true")
    modes.add_argument("--prepare-server", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--finish-server", type=int)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    if args.write_plan:
        args.output.mkdir(exist_ok=False, parents=True)
        write_json(args.output / "planned-trial.json", plan(repo))
    elif args.prepare_server:
        run = repo / "run"
        run.mkdir(exist_ok=True)
        require(not (run / LEVEL_NAME).exists(), "Refusing to reuse a world")
        with (run / "server.properties").open("x") as handle:
            handle.write("server-ip=127.0.0.1\nonline-mode=false\nmax-players=2\n"
                         f"level-name={LEVEL_NAME}\nlevel-seed={SEED}\n"
                         "enable-rcon=true\nrcon.port=25575\n"
                         f"rcon.password={os.environ['HEARTHBOUND_RCON_PASSWORD']}\n")
        (run / "eula.txt").write_text("eula=true\n")
    elif args.run:
        raise SystemExit(live(args.output))
    else:
        raise SystemExit(finish(args.output, args.finish_server))
