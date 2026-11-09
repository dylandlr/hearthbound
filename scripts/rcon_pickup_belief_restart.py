#!/usr/bin/env python3
"""Real server restart / lost-unsaved-NBT / world-swap acceptance. No AI inputs.

The outside-world checkpoint is read only by this test, never by citizens.
All edits below are labeled adversarial test fixtures on disposable CI worlds.
"""
import json
import re
import sys
import time
from pathlib import Path
from rcon_failed_pickup_reobservation import EX, SCOUT, A, B, D, MENU, check_count
from rcon_neural_report_haul import Rcon

CHECKPOINT = Path("pickup-restart-before.json")
FAILURES = 'ForgeData."hearthbound.pickupFailures.v1"'
REQUEST = 'ForgeData."hearthbound.pendingSourceRecheck.v1"'
HAUL = 'ForgeData."hearthbound.haul"'


def nbt(r, path):
    response = r.require(f"data get entity {EX} {path}", "entity data:")
    return response.split("entity data: ", 1)[1]


def field(receipt, name):
    match = re.search(r"\b" + re.escape(name) + r"=([^\s]+)", receipt)
    if not match:
        raise AssertionError("Missing " + name + ": " + receipt)
    return match.group(1)


def checkpoint(r, outcome, mode):
    outcome.update(mode=mode, failures_nbt=nbt(r, FAILURES), request_nbt=nbt(r, REQUEST),
                   uuid_nbt=nbt(r, "UUID"), haul_nbt=nbt(r, HAUL))
    CHECKPOINT.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")
    if mode == "clean":
        r.require("save-all flush", "Saved the game")
        r.run("stop")
    print("PICKUP_RESTART_CHECKPOINT_READY mode=" + mode, flush=True)


def no_choices(r):
    for command in ("hearthbound-report-choice", "hearthbound-report-mlp-choice"):
        receipt = r.require(f"{command} {EX} {A} {B} exposed", "selected=NONE")
        if "admissible_reports=0" not in receipt:
            raise AssertionError("Report mask did not fail closed: " + receipt)


def refresh(r, pos, count):
    r.require(f"hearthbound citizen_observe {pos} {SCOUT}", f"wheat={count}")
    r.require(f"hearthbound-share-direct {pos} {SCOUT} {EX}", "status=DELIVERED")


def verify(mode):
    before = json.loads(CHECKPOINT.read_text(encoding="utf-8"))
    result = dict(mode=mode, operator_triggered=True, autonomous_scouting=False,
                  crash_durable_negative_journal=False, rewards=0, model_updates=0)
    with Rcon() as r:
        r.run("forceload add 0 0")
        for _ in range(60):
            if "Test passed" in r.run(f"execute if entity {EX}"):
                break
            time.sleep(.1)
        else:
            raise AssertionError("Saved executor did not load")
        if nbt(r, "UUID") != before["uuid_nbt"]:
            raise AssertionError("Executor identity changed across restart")
        belief = r.run(f"hearthbound-pickup-belief {EX} {A}")
        same_world = field(belief, "world") == field(before["failed_pickup_receipt"], "world")
        if same_world != (mode != "world-swap"):
            raise AssertionError("World identity control failed")
        check_count(r, A, 0)
        check_count(r, B, 1)
        check_count(r, D, 0)
        no_choices(r)
        # A stale direct memory must not acquire a new session at delivery.
        r.require(f"hearthbound-share-direct {A} {SCOUT} {EX}",
                  "reason=REOBSERVATION_REQUIRED_AFTER_RESTART")

        if mode == "world-swap":
            for path, key in ((FAILURES, "failures_nbt"), (REQUEST, "request_nbt")):
                if nbt(r, path) != before[key]:
                    raise AssertionError("World-swap fixture changed citizen evidence")
            if "state=FAIL_CLOSED" not in belief:
                raise AssertionError("Foreign-world negatives were silently ignored")
            refresh(r, B, 1)
            no_choices(r)  # Fresh local report still cannot erase foreign evidence.
            r.require(f"hearthbound-reobserve-request {EX} {A}", "reason=FAIL_CLOSED_EVIDENCE")
            result["foreign_world_denied"] = True
        elif mode == "clean":
            if belief != before["failed_pickup_receipt"].replace(
                    "reobservation_request=NONE", "reobservation_request=AWAITING_SCOUT_DIRECT_OBSERVATION"):
                raise AssertionError("Failed-job receipt changed across clean restart: " + belief)
            for path, key in ((FAILURES, "failures_nbt"), (REQUEST, "request_nbt"), (HAUL, "haul_nbt")):
                if nbt(r, path) != before[key]:
                    raise AssertionError("Saved evidence changed: " + path)
            r.require(f"hearthbound-reobserve-request {EX} {A}", "reason=ALREADY_AWAITING_SCOUT")
            r.require(f"hearthbound-report-execution {EX} {before['first_job']}", "status=INCOMPLETE")
            # Fresh B makes these negative controls independent of the boot fence / TTL.
            refresh(r, B, 1)
            r.require(f"hearthbound-report-choice {EX} {A} {B} exposed", "selected=minecraft:overworld|7,101,1")
            mutations = (
                (FAILURES + ".entries[0].world", "[I;1,2,3,4]"),
                (FAILURES + ".entries[0].executor", "[I;1,2,3,4]"),
                (FAILURES + ".entries[0].failedTick", '"wrong-type"'),
                (FAILURES + ".entries[0].failedTick", "9223372036854775807L"),
                (FAILURES + ".entries", '["not-compounds"]'),
                (REQUEST + ".failedJob", "[I;1,2,3,4]"),
                (REQUEST + ".invalidatedReportId", '"wrong-report"'),
                (REQUEST + ".source", '"wrong-type"'),
            )
            for path, value in mutations:
                r.require(f"data modify entity {EX} {path} set value {value}", "Modified entity data")
                r.require(f"hearthbound-pickup-belief {EX} {A}", "state=FAIL_CLOSED")
                no_choices(r)
                r.require(f"hearthbound-reobserve-request {EX} {A}", "reason=FAIL_CLOSED_EVIDENCE")
                root, key = (FAILURES, "failures_nbt") if path.startswith(FAILURES) else (REQUEST, "request_nbt")
                r.require(f"data modify entity {EX} {root} set value {before[key]}", "Modified entity data")
            # Only no-cargo failed job cancellation is authorized.
            r.require(f"execute at {EX} run sable haul-cancel", "Unpicked haul cancelled")
            refresh(r, A, 0)
            r.require(f"hearthbound-pickup-belief {EX} {A}", "reobservation_request=FULFILLED_BY_NEW_DIRECT_REPORT")
            fulfilled = nbt(r, REQUEST)
            r.require(f"hearthbound-reobserve-request {EX} {A}", "reason=ALREADY_FULFILLED")
            if nbt(r, REQUEST) != fulfilled:
                raise AssertionError("Fulfilled request timestamp was laundered")
            refresh(r, B, 1)
            assigned = r.require(f"hearthbound-report-dispatch-trial {MENU} SCRIPTED exposed", "status=ASSIGNED")
            job = field(assigned, "job")
            if job == before["first_job"]:
                raise AssertionError("Recovery reused failed job")
            deadline = time.monotonic() + 85
            while time.monotonic() < deadline:
                receipt = r.run(f"hearthbound-report-execution {EX} {job}")
                if "status=EXECUTOR_COMPLETED" in receipt:
                    break
                time.sleep(.5)
            else:
                raise AssertionError("No physical recovery delivery")
            check_count(r, A, 0)
            check_count(r, B, 0)
            check_count(r, D, 1)
            if nbt(r, FAILURES) != before["failures_nbt"]:
                raise AssertionError("Recovery changed original negative event")
            result.update(exact_saved_evidence=True, malformed_controls=len(mutations),
                          second_job=job, completion=receipt, endpoints={"A": 0, "B": 0, "destination": 1})
        elif mode == "crash":
            # Failure/request must actually be missing, otherwise this trial did
            # not test the loss window and is not allowed to claim success.
            if "state=NONE" not in belief:
                raise AssertionError("Unsaved negative was not lost; crash control invalid")
            for path in (FAILURES, REQUEST, HAUL):
                if "Found no elements" not in r.run(f"data get entity {EX} {path}"):
                    raise AssertionError("Post-checkpoint data unexpectedly survived kill: " + path)
            for policy in ("SCRIPTED", "FROZEN_MLP"):
                r.require(f"hearthbound-report-dispatch-trial {MENU} {policy} exposed", "status=ABSTAIN")
            # Keep the old observed tick but forge current delivery time as an
            # adversarial replay: current session still cannot be minted by share.
            refresh(r, A, 0)
            refresh(r, B, 1)
            r.require(f"hearthbound-report-choice {EX} {A} {B} exposed", "selected=minecraft:overworld|7,101,1")
            result.update(unsaved_negative_lost=True, old_reports_denied=True,
                          fresh_observation_restores_choice=True, physical_recovery_claimed=False)
        else:
            raise ValueError(mode)
        Path("pickup-restart-" + mode + "-results.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8")
        r.require("save-all flush", "Saved the game")
        r.run("stop")
    print("REAL_FORGE_PICKUP_RESTART_PASS mode=" + mode, flush=True)


if __name__ == "__main__":
    verify(sys.argv[1])
