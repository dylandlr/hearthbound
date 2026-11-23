#!/usr/bin/env python3
"""Real delivery must finish its owned colony task even when dispatch is disabled.

Two autonomous assignments use one real citizen, followed by an unrelated
direct haul. Fixture positioning/replenishment occurs only before assignment.
There are no completion hooks, manufactured receipts, or behavioral retries.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import time
from uuid import UUID

from rcon_neural_report_haul import Rcon
from run_colony_reliability_trial import NbtReader

SABLE = "@e[type=minecraft:villager,name=Sable,limit=1]"
SOURCE, DESTINATION = "4 101 8", "14 101 8"
WORLD = Path("run/colony-completion-boundary-world")
BEFORE = Path("colony-completion-boundary-before.json")
UUID_TEXT = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")


def fields(text, marker):
    assert marker in text, text
    return dict(re.findall(r"\b([a-z_]+)=([^\s]+)", text.split(marker, 1)[1]))


def board(rcon):
    result = fields(rcon.require("hearthbound-colony audit", "COLONY_V1 "), "COLONY_V1 ")
    assert result.get("enabled") in ("true", "false"), result
    for key in ("queued", "assigned", "held", "done", "distinct_completed_citizens"):
        result[key] = int(result[key])
    return result


def state(rcon):
    before = board(rcon)
    history = fields(rcon.require("hearthbound-colony history-audit", "COLONY_HISTORY_V0_5 "),
                     "COLONY_HISTORY_V0_5 ")
    for key in ("records", "physically_completed", "assigned_without_verified_completion",
                "capacity_denials"):
        history[key] = int(history[key])
    reconciliation = fields(rcon.require("hearthbound-colony physical-reconciliation-audit",
                                        "COLONY_PHYSICAL_RECONCILIATION_V0_6 "),
                            "COLONY_PHYSICAL_RECONCILIATION_V0_6 ")
    claims = rcon.require("hearthboundclaims count", "Active source claims in this dimension:")
    match = re.search(r"Active source claims in this dimension: (\d+)", claims)
    assert match, claims
    after = board(rcon)
    assert before == after, "Board changed during terminal snapshot"
    return {"board": before, "history": history, "reconciliation": reconciliation,
            "outstanding_claims": int(match[1])}


def validate_state(observed, completed, pending=0):
    """Acceptance criteria do not infer completion from an inventory or phase alone."""
    b, h, r = observed["board"], observed["history"], observed["reconciliation"]
    assert b["enabled"] == "false", b
    assert b["queued"] == b["held"] == 0, b
    assert b["done"] == completed and b["assigned"] == pending, b
    assert b["distinct_completed_citizens"] == (1 if completed else 0), b
    assert h["records"] == completed + pending, h
    assert h["physically_completed"] == completed, h
    assert h["assigned_without_verified_completion"] == pending, h
    assert h["capacity_denials"] == 0, h
    assert int(r["done"]) == completed and int(r["assigned"]) == pending, r
    assert int(r["assigned_loaded_physically_complete"]) == 0, r
    assert int(r["assigned_unloaded"]) == 0, r
    assert int(r["assigned_loaded_incomplete"]) == pending, r
    assert r["strictly_read_only"] == "true" and r["reward_authorized"] == "false", r
    assert observed["outstanding_claims"] == pending, observed


def inventory(rcon, position, amount):
    if amount == 0:
        rcon.require(f"data get block {position} Items", "block data: []")
    else:
        rcon.require(f'execute if data block {position} '
                     f'Items[{{Slot:0b,id:"minecraft:wheat",Count:{amount}b}}]', "Test passed")
        rcon.run(f"data get block {position} Items")


def motor(rcon):
    text = rcon.require(f"execute at {SABLE} run sable haul-audit", "AUDIT job=")
    job = re.search(r"\bjob=(\S+)", text)
    phase = re.search(r"\bphase=(\d+)\b", text)
    assert job and UUID_TEXT.fullmatch(job[1]) and phase, text
    return {"job": job[1], "phase": int(phase[1]), "audit": text}


def validate_pending_motor(current):
    assert current["phase"] in (0, 1), "Delivery preceded the disabled-dispatch boundary"


def wait_for_citizen(rcon):
    """Readiness only: do not move, reload, respawn, or retry any physical job."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if "test passed" in rcon.run(f"execute if entity {SABLE}").lower():
            return
        time.sleep(0.25)
    raise AssertionError("Fixture citizen did not load within the fixed readiness window")


def parse_trace(text, expected_job):
    values = fields(text, "COLONY_TRACES_V0_4 ")
    assert values["count"] == "1", text
    assert values["learning_authorized"] == values["reward_authorized"] == "false", text
    encoded = re.search(r"\bentries=(.*?) learning_authorized=false", text)
    assert encoded and ";" not in encoded[1], text
    parts = encoded[1].split(",")
    assert len(parts) == 10, text
    task, citizen, job, decision, evidence, revision, observed, decided, assigned, delivered = parts
    assert all(UUID_TEXT.fullmatch(value) for value in (citizen, job, decision, evidence)), text
    assert job == expected_job, text
    task, revision, observed, decided, assigned, delivered = map(
        int, (task, revision, observed, decided, assigned, delivered))
    assert task > 0 and revision > 0 and 0 <= observed <= decided <= assigned <= delivered, text
    assert assigned - observed <= 20, text
    return {"task": task, "citizen": citizen, "job": job, "decision": decision,
            "evidence": evidence, "revision": revision, "observed": observed,
            "decided": decided, "assigned": assigned, "delivered": delivered,
            "episode": str(UUID(values["episode"]))}


def prepare_round(rcon, prior_deliveries):
    validate_state(state(rcon), prior_deliveries)
    inventory(rcon, SOURCE, 0)
    inventory(rcon, DESTINATION, prior_deliveries)
    # Independent task setup, performed only after the preceding motor completed.
    rcon.require(f'data merge block {SOURCE} '
                 '{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]}', "modified")
    rcon.require(f"tp {SABLE} 5 101 8", "Teleported")
    inventory(rcon, SOURCE, 1)


def wait_for_delivery(rcon, expected_job):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        current = motor(rcon)
        assert current["job"] == expected_job, "Physical job identity changed"
        if current["phase"] == 2:
            return current
        assert current["phase"] in (0, 1), current
        time.sleep(0.25)
    raise AssertionError("Active motor did not finish within the fixed 90-second window")


def autonomous_round(rcon, prior_deliveries):
    prepare_round(rcon, prior_deliveries)
    rcon.require("hearthbound-colony enable", "dispatch enabled")
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        current = board(rcon)
        assert current["done"] == prior_deliveries, "Missed the pre-delivery disable boundary"
        assert current["held"] == 0, current
        if current["assigned"] == 1:
            break
        time.sleep(0.05)
    else:
        raise AssertionError("Citizen did not autonomously assign the nearby source")
    rcon.require("hearthbound-colony disable", "Dispatch disabled")
    pending_motor = motor(rcon)
    validate_pending_motor(pending_motor)
    inventory(rcon, DESTINATION, prior_deliveries)
    pending = state(rcon)
    validate_state(pending, prior_deliveries, pending=1)
    completed_motor = wait_for_delivery(rcon, pending_motor["job"])
    inventory(rcon, SOURCE, 0)
    inventory(rcon, DESTINATION, prior_deliveries + 1)
    completed = state(rcon)
    validate_state(completed, prior_deliveries + 1)
    trace = parse_trace(rcon.require("hearthbound-colony decision-traces", "COLONY_TRACES_V0_4 "),
                        pending_motor["job"])
    return {"pending": pending, "pending_motor": pending_motor, "completed": completed,
            "completed_motor": completed_motor, "trace": trace}


class ColonyNbtReader(NbtReader):
    """Preserve the four-integer UUID arrays omitted by the world-seed reader."""
    def value(self, kind, depth=0):
        if kind == 11:
            count = self.number("i")
            if count != 4:
                raise ValueError("Unexpected integer array in bounded colony save")
            return [self.number("i") for _ in range(count)]
        return super().value(kind, depth)


def read_saved_data(name):
    raw = (WORLD / "data" / name).read_bytes()
    payload = gzip.decompress(raw)
    if len(payload) > 1024 * 1024:
        raise ValueError("Unexpected oversized fixture SavedData")
    return ColonyNbtReader(payload).root()["data"]


def saved_uuid(value):
    assert isinstance(value, list) and len(value) == 4, value
    assert all(type(part) is int for part in value), value
    return str(UUID(int=sum((part & 0xffffffff) << shift
                           for part, shift in zip(value, (96, 64, 32, 0)))))


def packed_position(position):
    x, y, z = map(int, position.split())
    packed = ((x & 0x3ffffff) << 38) | ((z & 0x3ffffff) << 12) | (y & 0xfff)
    return packed if packed < (1 << 63) else packed - (1 << 64)


def validate_persisted(saved, traces):
    assert len(traces) == 2 and len({entry["citizen"] for entry in traces}) == 1, traces
    assert len({entry["job"] for entry in traces}) == len({entry["task"] for entry in traces}) == 2
    tasks, history = saved["tasks"], saved["decisionHistory"]
    assert len(tasks) == len(history) == 2, saved
    assert saved["historyDeniedCapacity"] == 0, saved
    assert saved["destination"] == packed_position(DESTINATION), saved
    for trace in traces:
        task_matches = [entry for entry in tasks if entry["id"] == trace["task"]]
        history_matches = [entry for entry in history if entry["task"] == trace["task"]]
        assert len(task_matches) == len(history_matches) == 1, saved
        task, record = task_matches[0], history_matches[0]
        assert task["state"] == "DONE" and record["status"] == "PHYSICALLY_COMPLETED", saved
        assert saved_uuid(task["owner"]) == saved_uuid(record["citizen"]) == trace["citizen"]
        assert saved_uuid(task["job"]) == saved_uuid(record["job"]) == trace["job"]
        assert task["assignedTick"] == record["assigned"] == trace["assigned"]
        assert task["dimension"] == "minecraft:overworld", task
        for key, position in (("source", SOURCE), ("destination", DESTINATION)):
            assert task[key] == record[key] == packed_position(position), saved
        for key in ("observed", "decided", "delivered", "revision"):
            assert record[key] == trace[key], saved
        for key in ("decision", "evidence", "episode"):
            assert saved_uuid(record[key]) == trace[key], saved


def tested_commit():
    value = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    expected = os.environ.get("HEARTHBOUND_EXPECTED_COMMIT")
    assert not expected or value == expected, "Checkout differs from requested head"
    return value


def before_restart():
    commit = tested_commit()
    with Rcon() as rcon:
        for command in (
            "gamerule doMobSpawning false", "forceload add -16 -16 31 31",
            "fill 0 100 4 20 106 12 minecraft:air",
            "fill 0 100 4 20 100 12 minecraft:stone",
            f"setblock {SOURCE} minecraft:chest replace",
            f"setblock {DESTINATION} minecraft:chest replace",
        ):
            rcon.run(command)
        rcon.require("execute positioned 5 101 8 run sable spawn", "Sable spawned")
        wait_for_citizen(rcon)
        rcon.require(f"hearthbound-colony set-destination {DESTINATION}", "Registered shared destination")
        rounds = [autonomous_round(rcon, n) for n in range(2)]
        traces = [entry["trace"] for entry in rounds]
        assert traces[0]["citizen"] == traces[1]["citizen"], traces
        assert traces[0]["job"] != traces[1]["job"] and traces[0]["task"] != traces[1]["task"], traces
        assert traces[0]["delivered"] <= traces[1]["assigned"], traces
        # A direct haul must not retroactively complete or create a colony task.
        prepare_round(rcon, 2)
        rcon.require(f"execute at {SABLE} run sable haul {SOURCE} {DESTINATION}",
                     "Sable assigned wheat haul")
        direct = motor(rcon)
        assert direct["job"] not in {entry["job"] for entry in traces}, direct
        wait_for_delivery(rcon, direct["job"])
        inventory(rcon, SOURCE, 0)
        inventory(rcon, DESTINATION, 3)
        final = state(rcon)
        validate_state(final, 2)
        time.sleep(2.2)
        assert state(rcon) == final, "Idle ticks duplicated completion evidence"
        rcon.require("save-all flush", "Saved the game")
        persisted = read_saved_data("hearthbound_colony_tasks_v1.dat")
        validate_persisted(persisted, traces)
        world = read_saved_data("hearthbound_world_identity_v1.dat")["worldUuid"]
        result = {"schema": "hearthbound.colony-completion-boundary.v1",
                  "tested_commit": commit, "world": str(UUID(world)), "rounds": rounds,
                  "unrelated_direct_job": direct["job"], "final": final, "persisted": persisted,
                  "physical_deliveries": 3, "colony_completed_tasks": 2, "distinct_workers": 1,
                  "dispatch_disabled_before_each_delivery": True,
                  "completion_receipts_manufactured": False, "behavioral_retries": 0,
                  "learned_collaboration": False, "inventory_crash_atomicity_verified": False}
        BEFORE.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        print("COLONY_COMPLETION_BOUNDARY_PASS physical_deliveries=3 colony_done=2 history_complete=2 "
              "distinct_workers=1 dispatch_disabled=true unrelated_job_credited=false", flush=True)
        rcon.run("stop")


def after_restart():
    prior = json.loads(BEFORE.read_text())
    assert prior["tested_commit"] == tested_commit()
    with Rcon() as rcon:
        wait_for_citizen(rcon)
        current = state(rcon)
        validate_state(current, 2)
        assert current == prior["final"], "Restart changed completed board/history evidence"
        inventory(rcon, SOURCE, 0)
        inventory(rcon, DESTINATION, 3)
        current_motor = motor(rcon)
        assert current_motor["job"] == prior["unrelated_direct_job"] and current_motor["phase"] == 2
        time.sleep(2.2)
        assert state(rcon) == current, "Restart/idle tick duplicated completion evidence"
        rcon.require("save-all flush", "Saved the game")
        persisted = read_saved_data("hearthbound_colony_tasks_v1.dat")
        validate_persisted(persisted, [entry["trace"] for entry in prior["rounds"]])
        assert persisted == prior["persisted"], "Persisted task/history identities changed"
        assert read_saved_data("hearthbound_world_identity_v1.dat")["worldUuid"] == prior["world"]
        Path("colony-completion-boundary-after.json").write_text(json.dumps({
            "schema": "hearthbound.colony-completion-boundary-restart.v1",
            "tested_commit": prior["tested_commit"], "world": prior["world"],
            "state": current, "persisted": persisted,
            "clean_restart_preserved_jobs": True, "dispatch_enabled": False,
            "duplicate_completion_observed": False, "crash_atomicity_verified": False,
        }, indent=2, sort_keys=True) + "\n")
        print("COLONY_COMPLETION_BOUNDARY_RESTART_PASS tasks=2 history_complete=2 "
              "same_citizen=true dispatch_disabled=true duplicated_completion=false", flush=True)
        rcon.run("stop")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    args = parser.parse_args()
    try:
        (before_restart if args.phase == "before" else after_restart)()
    except Exception as error:
        failure = {"schema": "hearthbound.colony-completion-boundary-failure.v1",
                   "phase": args.phase, "status": "FAILED", "error_type": type(error).__name__,
                   "error": str(error), "behavioral_retries": 0}
        try:
            with Rcon() as diagnostic:
                failure["state"] = state(diagnostic)
                failure["motor"] = motor(diagnostic)
                failure["source"] = diagnostic.run(f"data get block {SOURCE} Items")
                failure["destination"] = diagnostic.run(f"data get block {DESTINATION} Items")
        except Exception as unavailable:
            failure["diagnostic_error"] = type(unavailable).__name__ + ": " + str(unavailable)
        Path(f"colony-completion-boundary-{args.phase}-failure.json").write_text(
            json.dumps(failure, indent=2, sort_keys=True) + "\n")
        raise
