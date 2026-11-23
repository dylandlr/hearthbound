#!/usr/bin/env python3
"""Real Forge communication provenance, physical delivery, and clean-save restart.

The scripted policy and candidate menu are operator-controlled. This tests
records and a withheld-input control, not a causal topology/performance claim.
"""
import argparse
import json
import re
import subprocess
import time
from pathlib import Path

from rcon_neural_report_haul import Rcon, count

SABLE = "@e[type=minecraft:villager,name=Sable,limit=1]"
SCOUT = "@e[type=minecraft:villager,tag=hb_communication_scout,limit=1]"
A, B, DEST = "3 101 1", "7 101 1", "10 101 2"
DISPATCH = f"hearthbound-report-dispatch-trial {SABLE} {A} {B} {DEST} scripted"


def audit(rcon):
    text = rcon.require("hearthbound-communication audit", "CITIZEN_COMMUNICATION_AUDIT_V1")
    values = dict(re.findall(r"\b([a-z_]+)=([^\s]+)", text))
    for key in ("send_attempts", "rejected_sends", "duplicate_sends", "messages", "events",
                "delivered", "read", "selected", "assigned", "physical_completed",
                "capacity_denials", "recording_errors"):
        values[key] = int(values[key])
    assert values["capacity_denials"] == values["recording_errors"] == 0, values
    assert values["attempt_capacity_denials"] == "0", values
    assert values["history_quarantined"] == "false", values
    assert values["strictly_read_only"] == "true", values
    assert values["causal_benefit_established"] == "false", values
    return values


def records(rcon, kind):
    result = []
    total = None
    while total is None or len(result) < total:
        text = rcon.require(f"hearthbound-communication {kind} {len(result)}",
                            f"CITIZEN_COMMUNICATION_{kind.upper()}_V1 ")
        page = json.loads(text.split("_V1 ", 1)[1])
        assert page["kind"] == kind and page["offset"] == len(result), page
        assert page["strictly_read_only"] is True
        assert page["inventory_delta_verified"] is False
        assert page["causal_benefit_established"] is False
        if total is not None:
            assert page["total"] == total, "History changed while paginating"
        total = page["total"]
        if not page["records"]:
            assert len(result) == total, "Truncated communication export"
            break
        result.extend(page["records"])
    assert len(result) == total
    return result


def snapshot(rcon):
    before = audit(rcon)
    messages, events = records(rcon, "messages"), records(rcon, "events")
    attempts = records(rcon, "attempts")
    assert audit(rcon) == before, "Inspection mutated communication evidence"
    assert len(messages) == before["messages"] and len(events) == before["events"]
    return {"audit": before, "messages": messages, "events": events, "attempts": attempts}


def validate_chain(data):
    """Fail closed on mixed recipients/jobs or a selected-but-unexecuted report."""
    messages, events = data["messages"], data["events"]
    assert len(messages) == 2 and len(events) == 7
    by_id = {m["id"]: m for m in messages}
    assert len(by_id) == 2
    assert len({m["sender"] for m in messages}) == len({m["recipient"] for m in messages}) == 1
    for message in messages:
        assert message["sender"] != message["recipient"]
        assert message["world"] == data["audit"]["world"]
        assert message["episode"] == messages[0]["episode"]
        assert message["observed_tick"] <= message["sent_tick"] == message["delivered_tick"]
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    expected_counts = {"DELIVERED": 2, "READ": 2, "SELECTED": 1,
                       "ASSIGNED": 1, "PHYSICAL_COMPLETED": 1}
    for stage, total in expected_counts.items():
        assert sum(e["stage"] == stage for e in events) == total
    for stage in ("DELIVERED", "READ"):
        assert sorted(e["message_id"] for e in events if e["stage"] == stage) == sorted(by_id)
    linked = [e for e in events if e["stage"] in ("SELECTED", "ASSIGNED", "PHYSICAL_COMPLETED")]
    assert len({e["message_id"] for e in linked}) == len({e["decision_id"] for e in linked}) == 1
    assert linked[1]["job_id"] == linked[2]["job_id"]
    assert [e["stage"] for e in linked] == ["SELECTED", "ASSIGNED", "PHYSICAL_COMPLETED"]
    assert max(e["sequence"] for e in events if e["stage"] == "READ") < linked[0]["sequence"]
    assert linked[1]["destination"] == linked[2]["destination"] == "minecraft:overworld|10,101,2"
    selected = by_id[linked[0]["message_id"]]
    assert selected["source"] == "minecraft:overworld|3,101,1"
    assert linked[2]["wheat_transferred"] == 1
    assert linked[2]["witness"] == "EXECUTOR_INSERTION_RETURNED_NO_REMAINDER"
    for event in events:
        message = by_id[event["message_id"]]
        assert event["actor"] == message["recipient"]
        assert event["tick"] >= message["delivered_tick"]
    decision_events = [e for e in events if e["stage"] != "DELIVERED"]
    assert len({e["decision_id"] for e in decision_events}) == 1
    assert [e["tick"] for e in decision_events] == sorted(e["tick"] for e in decision_events)
    return linked[2]["job_id"]


def before_restart():
    with Rcon() as rcon:
        initial = audit(rcon)
        assert initial["messages"] == initial["events"] == initial["send_attempts"] == 0
        for command in (
            "gamerule doMobSpawning false", "forceload add 0 0",
            "fill 0 99 0 12 105 4 minecraft:air", "fill 0 100 0 12 100 4 minecraft:stone",
            'setblock 3 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:3b}]} replace',
            'setblock 7 101 1 minecraft:chest{Items:[{Slot:0b,id:"minecraft:wheat",Count:1b}]} replace',
            "setblock 10 101 2 minecraft:chest replace",
        ):
            rcon.run(command)
        rcon.require("execute positioned 2 101 2 run sable spawn", "Sable spawned")
        rcon.require(f"tp {SABLE} 2 101 2", "Teleported")
        rcon.require('summon minecraft:villager 4 101 3 {Tags:["hb_communication_scout"],'
                     'ForgeData:{"hearthbound.citizen":1b},NoAI:1b}', "Summoned new")
        rcon.require(f"hearthbound-share-direct {A} {SCOUT} {SABLE}", "reason=NO_DIRECT_EVIDENCE")
        for source, wheat in ((A, 3), (B, 1)):
            rcon.require(f"hearthbound citizen_observe {source} {SCOUT}", f"wheat={wheat}")
            rcon.require(f"hearthbound-share-direct {source} {SCOUT} {SABLE}", "status=DELIVERED")
        rcon.require(f"hearthbound-share-direct {A} {SCOUT} {SABLE}", "status=DUPLICATE")
        delivered = snapshot(rcon)
        assert delivered["audit"]["send_attempts"] == 4
        assert delivered["audit"]["rejected_sends"] == delivered["audit"]["duplicate_sends"] == 1
        assert delivered["audit"]["delivered"] == 2 and delivered["audit"]["read"] == 0
        assert [a["outcome"] for a in delivered["attempts"]] == ["REJECTED", "DELIVERED", "DELIVERED", "DUPLICATE"]
        assert delivered["attempts"][0]["reason"] == "NO_DIRECT_EVIDENCE"
        assert len({a["sender"] for a in delivered["attempts"]}) == 1
        assert len({a["recipient"] for a in delivered["attempts"]}) == 1
        for source in (A, B):
            rcon.require(f"hearthbound knowledge_report {source} {SABLE}", "status=REPORTED")
            rcon.require(f"hearthbound citizen_memory {source} {SABLE}", "status=UNKNOWN")
        rcon.require(f"hearthbound-report-choice {SABLE} {A} {B} exposed", "status=CHOOSE")
        rcon.require(f"{DISPATCH} withheld", "status=ABSTAIN")
        assert snapshot(rcon) == delivered, "Shadow/withheld query falsely recorded use"
        count(rcon, A, 3); count(rcon, B, 1); count(rcon, DEST, 0)
        dispatch = rcon.require(f"{DISPATCH} exposed", "status=ASSIGNED")
        job = re.search(r"\bjob=([a-f0-9-]{36})", dispatch).group(1)
        decision = re.search(r"\bcommunication_decision=([a-f0-9-]{36})", dispatch).group(1)
        for _ in range(135):
            execution = rcon.run(f"hearthbound-report-execution {SABLE} {job}")
            if "status=EXECUTOR_COMPLETED" in execution:
                break
            if "status=DENIED" in execution:
                raise AssertionError(execution)
            time.sleep(1)
        else:
            raise AssertionError("Communication-linked hauling did not complete: " + execution)
        count(rcon, A, 2); count(rcon, B, 1); count(rcon, DEST, 1)
        final = snapshot(rcon)
        assert validate_chain(final) == job
        assert {e["decision_id"] for e in final["events"] if "decision_id" in e} == {decision}
        result = {
            "schema": "hearthbound.communication-physical-acceptance.v1",
            "tested_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
            "origin": "REAL_FORGE_AUTHORITATIVE_WORLD", "policy": "SCRIPTED_REPORT_RANK_V1",
            "history": final, "dispatch": dispatch,
            "physical_inventory_deltas": {"source_a": [3, 2], "source_b": [1, 1], "destination": [0, 1]},
            "withheld_and_shadow_history_unchanged": True,
            "causal_benefit_established": False, "learned_collaboration": False,
            "autonomous_communication": False, "inventory_journal_crash_atomicity": False,
        }
        Path("citizen-communication-before.json").write_text(json.dumps(result, indent=2) + "\n")
        rcon.require("save-all flush", "Saved the game")
        print("CITIZEN_COMMUNICATION_PHYSICAL_PASS messages=2 read=2 selected=1 assigned=1 "
              "physical_completed=1 source_a=3_to_2 destination=0_to_1", flush=True)
        rcon.run("stop")


def after_restart():
    before = json.loads(Path("citizen-communication-before.json").read_text())["history"]
    with Rcon() as rcon:
        after = snapshot(rcon)
        assert after["messages"] == before["messages"] and after["events"] == before["events"]
        assert after["attempts"] == before["attempts"]
        assert after["audit"]["world"] == before["audit"]["world"]
        assert after["audit"]["episode"] != before["audit"]["episode"]
        for key in before["audit"]:
            if key != "episode":
                assert after["audit"][key] == before["audit"][key], key
        rcon.require(f"{DISPATCH} exposed", "status=ABSTAIN")
        assert snapshot(rcon) == after, "Historical reports became new-session decision authority"
        validate_chain(after)
        count(rcon, A, 2); count(rcon, B, 1); count(rcon, DEST, 1)
        Path("citizen-communication-after.json").write_text(json.dumps({
            "schema": "hearthbound.communication-clean-restart.v1", "history": after,
            "clean_save_history_preserved": True, "stale_session_dispatch_abstained": True,
            "crash_atomicity_verified": False,
        }, indent=2) + "\n")
        print("CITIZEN_COMMUNICATION_RESTART_PASS history_preserved=true stale_report_authority=false", flush=True)
        rcon.run("stop")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    args = parser.parse_args()
    try:
        (before_restart if args.phase == "before" else after_restart)()
    except Exception as error:
        failure = {"schema": "hearthbound.communication-acceptance-failure.v1",
                   "phase": args.phase, "status": "FAILED",
                   "error_type": type(error).__name__, "error": str(error),
                   "history": None, "physical_outcome": None,
                   "causal_benefit_established": False}
        try:
            with Rcon() as diagnostic:
                failure["history"] = snapshot(diagnostic)
        except Exception as unavailable:
            failure["diagnostic_error"] = type(unavailable).__name__ + ": " + str(unavailable)
        Path(f"citizen-communication-{args.phase}-failure.json").write_text(
            json.dumps(failure, indent=2) + "\n")
        raise
