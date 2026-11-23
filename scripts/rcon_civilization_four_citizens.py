#!/usr/bin/env python3
"""Live, opt-in Hearthbound colony acceptance on a disposable Forge server.

Four real marked villagers observe separate wheat inventories, propose work
without operator-enqueued hauling tasks, share one colony task board, and
physically move exactly one item each. This does not claim learned behavior.
"""
import json
import re
import os
import socket
import struct
import time

from rcon_two_citizen_haul_acceptance import Rcon, packet, exact

PASS = "test passed"
SOURCES = (4, 12, 20, 28)
DESTINATION = 16


def check(rcon, command, substring):
    response = rcon.run(command)
    if substring.lower() not in response.lower():
        raise AssertionError(f"Expected {substring!r}: {command}: {response}")
    return response


def wheat_count(rcon, x, amount):
    return PASS in rcon.run(
        f'execute if data block {x} 100 1 Items[{{id:"minecraft:wheat",Count:{amount}b}}]'
    ).lower()


def run_trial(rcon, sleep=time.sleep):
    check(rcon, "forceload add 0 0 31 4", "force loaded")
    check(rcon, "fill 0 99 0 31 99 4 minecraft:stone", "filled")
    check(rcon, "fill 0 100 0 31 103 4 minecraft:air", "filled")

    for x in (*SOURCES, DESTINATION):
        check(rcon, f"setblock {x} 100 1 minecraft:chest replace", "changed the block")
    for x in SOURCES:
        check(rcon, f'data merge block {x} 100 1 {{Items:[{{Slot:0b,id:"minecraft:wheat",Count:1b}}]}}', "modified")

    for x in SOURCES:
        check(rcon, f"execute positioned {x+1} 100 2 run sable spawn", "Sable spawned")
    check(rcon, f"hearthbound-colony set-destination {DESTINATION} 100 1",
          "Registered shared destination")
    before = check(rcon, "hearthbound-colony audit", "queued=0")
    if "assigned=0" not in before or "done=0" not in before:
        raise AssertionError("Board was not initially empty: " + before)

    check(rcon, "hearthbound-colony enable", "dispatch enabled")
    success = False
    for poll in range(150):
        sleep(1)
        if poll % 5 != 0:
            continue
        audit = check(rcon, "hearthbound-colony audit", "COLONY_V1")
        if "done=4" in audit:
            success = True
            break
        if poll in (20, 60, 100):
            print("CIVILIZATION_PROGRESS poll=" + str(poll) + " " + audit, flush=True)
            rcon.run("hearthbound-colony physical-reconciliation-audit")
            rcon.run("hearthbound-colony history-audit")

    if not success:
        # Preserve read-only evidence of the missed opportunity and citizen
        # positions; never issue additional assignments or teleport agents.
        for x in SOURCES:
            rcon.run(f"data get block {x} 100 1 Items")
            rcon.run(
                f"execute positioned {x+1} 100 2 run "
                "execute if entity @e[type=minecraft:villager,name=Sable,distance=..6]"
            )
        rcon.run(f"data get block {DESTINATION} 100 1 Items")
        rcon.run("hearthboundclaims count")
        rcon.run("hearthbound-colony physical-reconciliation-audit")
        rcon.run("hearthbound-colony history-audit")
        # Terminal observation only: an intermediate 3/4 poll is not a failure.
        print("HEARTHBOUND_TERMINAL_ACCOUNTING_V1 " + json.dumps({
            "done": int(re.search(r"\bdone=(\d+)", audit).group(1)),
            "destination_has_four_wheat": wheat_count(rcon, DESTINATION, 4),
            "deadline_exhausted": True,
        }, sort_keys=True), flush=True)
        raise AssertionError("Four independently observed jobs did not complete: " + audit)

    for x in SOURCES:
        # Empty chest must not still contain a wheat entry with count 1.
        if wheat_count(rcon, x, 1):
            raise AssertionError(f"Source {x} still contains original wheat")
    if not wheat_count(rcon, DESTINATION, 4):
        raise AssertionError("Destination lacks exact 4-wheat physical inventory")
    check(rcon, "hearthboundclaims count", "Active source claims in this dimension: 0")
    reconciliation = check(rcon, "hearthbound-colony physical-reconciliation-audit",
                           "COLONY_PHYSICAL_RECONCILIATION_V0_6")
    for expected in ("assigned=0", "assigned_loaded_physically_complete=0",
                     "assigned_unloaded=0", "done=4",
                     "strictly_read_only=true"):
        if expected not in reconciliation:
            raise AssertionError("Physical/queue discrepancy at acceptance: " + reconciliation)
    final = check(rcon, "hearthbound-colony audit", "done=4")
    if "held=0" not in final or "assigned=0" not in final:
        raise AssertionError("Unresolved jobs after delivery: " + final)
    if "distinct_completed_citizens=4" not in final:
        raise AssertionError("Jobs were not completed by four distinct citizens: " + final)
    check(rcon, "hearthbound-colony decision-audit", "latest_scoped_completed_citizens=4")
    history_audit = check(rcon, "hearthbound-colony history-audit", "COLONY_HISTORY_V0_5")
    for expected in ("records=4", "physically_completed=4",
                     "assigned_without_verified_completion=0", "capacity_denials=0",
                     "reward_authorized=false"):
        if expected not in history_audit:
            raise AssertionError("Incomplete persisted citizen decision history: " + history_audit)
    trace_output = check(rcon, "hearthbound-colony decision-traces", "COLONY_TRACES_V0_4")
    if "count=4" not in trace_output or "learning_authorized=false" not in trace_output:
        raise AssertionError("Missing four scoped physical decision traces: " + trace_output)
    trace_match = re.search(r"entries=(.*?) learning_authorized=false", trace_output)
    if not trace_match:
        raise AssertionError("Malformed decision trace envelope: " + trace_output)
    entries = []
    for encoded in trace_match.group(1).split(";"):
        fields = encoded.split(",")
        if len(fields) != 10 or not all(fields):
            raise AssertionError("Incomplete citizen decision trace: " + encoded)
        task, citizen, job, decision, evidence, revision, observed, decided, assigned, delivered = fields
        if not all(re.fullmatch(r"[0-9a-fA-F-]{36}", ident) for ident in
                   (citizen, job, decision, evidence)):
            raise AssertionError("Invalid trace identity: " + encoded)
        try:
            task_id, revision_id, t0, t1, t2, t3 = map(
                int, (task, revision, observed, decided, assigned, delivered))
        except ValueError as error:
            raise AssertionError("Non-numeric trace chronology: " + encoded) from error
        if not (task_id > 0 and revision_id > 0 and 0 <= t0 <= t1 <= t2 <= t3
                and t2 - t0 <= 20):
            raise AssertionError("Invalid decision chronology: " + encoded)
        entries.append({
            "task_id": task_id, "citizen": citizen, "job": job,
            "decision": decision, "evidence": evidence,
            "revision": revision_id, "observed_tick": t0,
            "decision_tick": t1, "assigned_tick": t2, "delivered_tick": t3,
        })
    if len(entries) != 4 or any(len({e[key] for e in entries}) != 4
                                for key in ("task_id", "citizen", "job", "decision", "evidence")):
        raise AssertionError("Traces do not identify four distinct completed jobs")
    print("HEARTHBOUND_CITIZEN_TRACES_V1 " +
          json.dumps({"schema": "hearthbound.citizen_decisions.v1",
                      "count": 4, "entries": entries,
                      "scope": "LOADED_LATEST_CITIZEN_MEMORY_AND_PHYSICAL_JOB",
                      "policy": "DETERMINISTIC_TRAIT_RANK_V1",
                      "learning_authorized": False},
                     sort_keys=True, separators=(",", ":")), flush=True)
    check(rcon, "hearthbound-colony disable", "Dispatch disabled")
    print("CIVILIZATION_FOUR_CITIZEN_ACCEPTANCE_PASS "
          "observed_proposals=4 physical_deliveries=4 destination_wheat=4 "
          "outstanding_claims=0 scoped_citizen_decisions=4 no_reward_claim=true", flush=True)
    # Export aggregate-only verified evidence for offline MARBLE-style analysis.
    # No invented individual citizen IDs or milestone participation credit.
    # This output is trustworthy only when bound to this passing live CI job.
    receipt = {
        "schema": "hearthbound.four_citizen_physical.v1",
        "fixture_world": "four-citizen-colony",
        "fixture_seed": os.environ.get("HEARTHBOUND_WORLD_SEED", "hearthbound-four-citizen-v0-3"),
        "verification": {
            "source_chests_without_original_wheat": 4,
            "destination_wheat": 4,
            "outstanding_claims": 0,
            "distinct_completed_citizens": 4,
            "scoped_citizen_decisions": 4,
            "dispatch_disabled_at_end": True,
        },
        "aggregate_milestone": {
            "id": "four-independent-wheat-deliveries",
            "completed": True,
            "physical_units": 4,
            "individual_contributors": None,
        },
        "limits": {
            "individual_contribution_scores": False,
            "independent_world_replicate": False,
            "learned_policy": False,
            "journal_crash_atomicity": False,
        }
    }
    print("HEARTHBOUND_BENCHMARK_RECEIPT_V1 " +
          json.dumps(receipt, sort_keys=True, separators=(",", ":")), flush=True)


def main():
    with socket.create_connection(("127.0.0.1", 25575), timeout=15) as sock:
        sock.settimeout(20)
        sock.sendall(packet(1, 3, os.environ["HEARTHBOUND_RCON_PASSWORD"]))
        for _ in range(4):
            size = struct.unpack("<i", exact(sock, 4))[0]
            if not 10 <= size <= 1000000:
                raise ValueError("Bad RCON authorization frame")
            frame = exact(sock, size)
            request_id, response_type = struct.unpack("<ii", frame[:8])
            if request_id == 1:
                if response_type != 2:
                    raise AssertionError("RCON authentication failed")
                break
        else:
            raise AssertionError("No RCON authorization response")
        run_trial(Rcon(sock))


if __name__ == "__main__":
    main()
