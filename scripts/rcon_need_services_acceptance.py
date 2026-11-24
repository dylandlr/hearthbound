#!/usr/bin/env python3
"""One actual Forge need/request/service cycle and a clean stopped restart.

This is an engineering acceptance, not a learned-policy experiment. Two mobile
citizens have identical capabilities. Public site geometry is configured, but
stock and demand observations are local. No operator travel, handoff, pickup,
or completion command is issued after start. Native inventories are mandatory
witnesses; runtime message and completion counters are not substitutes.
"""
import argparse
import json
import os
from pathlib import Path
import re
import time
from uuid import UUID

from rcon_private_communication_trial import connection

COMMAND = "hearthbound-services"
SOURCE = (36, 101, 3)
BUFFER = (4, 101, 3)
INITIAL = 8
TARGET = 2
DEADLINE_SECONDS = 240
QUIET_SECONDS = 10
SCHEMA = "hearthbound.need-service-live-acceptance.v1"


def require(condition, explanation):
    if not condition:
        raise AssertionError(explanation)


def xyz(point):
    return " ".join(map(str, point))


def response_json(text, marker):
    require(marker in text, "Missing runtime response marker: " + text)
    value = json.loads(text.split(marker, 1)[1].strip())
    require(isinstance(value, dict), "Runtime response must be an object")
    return value


def status(rcon):
    value = response_json(rcon.run(COMMAND + " status"), "NEED_SERVICES_STATUS")
    required = ("enabled", "enrolled", "assigned", "transfers", "held",
                "records_total", "capacity_denials", "production_credits",
                "active_commitments", "cost_updates")
    require(all(key in value for key in required), "Incomplete service status: " + repr(value))
    require(type(value["enabled"]) is bool, "Enabled must be a boolean")
    for key in required[1:]:
        require(type(value[key]) is int and value[key] >= 0, "Invalid status count: " + key)
    require(value["production_credits"] == 0,
            "Chest transfer must not be admitted as Create production")
    require(value["capacity_denials"] == 0, "Evidence capacity exhausted")
    require(not value.get("errors"), "Runtime reported errors: " + repr(value))
    require(not value.get("failure"), "Runtime reported failure: " + repr(value))
    return value


def inventory_value(text):
    """Parse an independent native Items-list witness, accepting wheat only."""
    first, last = text.find("["), text.rfind("]")
    require(first >= 0 and last >= first, "Native inventory list absent: " + text)
    raw = text[first:last + 1]
    if raw.strip() == "[]":
        return 0
    ids = re.findall(r'\bid:\s*"([^"]+)"', raw)
    amounts = re.findall(r"\bCount:\s*(-?\d+)b\b", raw)
    require(ids and len(ids) == len(amounts), "Malformed inventory witness: " + raw)
    require(all(item == "minecraft:wheat" for item in ids), "Unexpected material: " + raw)
    require(all(0 < int(count) <= 64 for count in amounts), "Invalid stack count: " + raw)
    return sum(map(int, amounts))


def witness(rcon, point, expected):
    raw = rcon.run("data get block " + xyz(point) + " Items")
    actual = inventory_value(raw)
    require(actual == expected, f"Physical inventory differs at {point}: {actual} != {expected}")
    if expected:
        rcon.require(f'execute if data block {xyz(point)} '
                     f'Items[{{Slot:0b,id:"minecraft:wheat",Count:{expected}b}}]', "Test passed")
    return {"position": list(point), "count": actual, "native_response": raw}


def records(rcon, expected):
    result = []
    while len(result) < expected:
        page = response_json(rcon.run(f"{COMMAND} records {len(result)}"),
                             "NEED_SERVICES_RECORDS")
        require(page.get("offset") == len(result), "Wrong event-page offset")
        require(type(page.get("total")) is int and page["total"] >= expected,
                "Event history disappeared")
        rows = page.get("records")
        require(isinstance(rows, list) and rows, "Missing event page")
        result.extend(rows[:expected - len(result)])
    require([row.get("sequence") for row in result] == list(range(1, expected + 1)),
            "Duplicate, missing, or reordered event records")
    return result


def validate_chain(events, units=TARGET):
    """Trace validation is necessary, but the caller must also witness inventories."""
    received = [row for row in events if row.get("type") == "REQUEST_RECEIVED"]
    sent = [row for row in events if row.get("type") == "REQUEST_SENT"]
    observed = [row for row in events if row.get("type") == "NEED_OBSERVED"]
    assigned = [row for row in events if row.get("type") == "MOTOR_ASSIGNED"]
    completed = [row for row in events if row.get("type") == "TRANSFER_VERIFIED"]
    require(observed and sent and received, "A typed request was not observed, sent, and received")
    carries = [row for row in events if row.get("type") == "OPTION_STARTED"
               and row.get("option", row.get("detail")) == "CARRY_REQUEST"]
    require(carries, "No persistent request-carrying option was exercised")
    require(len(completed) == units, "Wrong number of verified native transfers")
    require(len({row.get("job") for row in assigned}) == len(assigned),
            "A physical job was assigned twice")
    require(len({row.get("job") for row in completed}) == len(completed),
            "A physical completion was credited twice")
    recipient_link = False
    for completion in completed:
        require(str(UUID(completion["job"])) == completion["job"], "Noncanonical native job UUID")
        require(completion.get("units") == 1 and completion.get("receipt"),
                "Missing independent native executor receipt")
        binding = [row for row in assigned if row.get("job") == completion["job"]]
        require(len(binding) == 1, "Completion lacks its unique motor assignment")
        assignment = binding[0]
        require(assignment.get("citizen") == completion.get("citizen"), "Completion changed executor")
        require(assignment.get("commitment") and
                assignment["commitment"] == completion.get("commitment"), "Completion changed commitment")
        require(assignment["tick"] <= completion["assigned_tick"]
                <= completion["delivered_tick"] <= completion["tick"], "Invalid native chronology")
        require(assignment["sequence"] < completion["sequence"], "Completion precedes assignment")
        if assignment.get("origin") != "REPORT":
            continue
        packet = assignment.get("selected_packet")
        require(packet, "Report-selected job lacks its selected packet ID")
        deliveries = [row for row in received if row.get("packet") == packet]
        require(len(deliveries) == 1, "Selected packet lacks a unique actual delivery")
        delivery = deliveries[0]
        require(delivery.get("recipient") == delivery.get("citizen") == assignment.get("citizen"),
                "Selected packet was delivered to another citizen")
        require(delivery.get("request") == assignment.get("request")
                and delivery.get("revision") == assignment.get("revision"), "Selected request revision differs")
        transmissions = [row for row in sent if row.get("packet") == packet]
        require(len(transmissions) == 1, "Selected packet lacks a unique actual send")
        transmission = transmissions[0]
        for key in ("request", "revision", "observer", "observed_tick", "sender", "recipient"):
            require(key in transmission and transmission[key] == delivery.get(key),
                    "Packet changed between send and delivery: " + key)
        require(transmission.get("citizen") == transmission["sender"] != transmission["recipient"],
                "Packet sender identity differs or is the recipient")
        witnesses = [row for row in observed if row.get("request") == transmission["request"]
                     and row.get("revision") == transmission["revision"]
                     and row.get("observer") == transmission["observer"]
                     and row.get("citizen") == transmission["observer"]
                     and row.get("observed_tick") == transmission["observed_tick"]
                     and row["sequence"] < transmission["sequence"]]
        require(witnesses, "Packet lacks its original need observation")
        claims = [row for row in events if row.get("type") == "SUPPLY_CLAIMED"
                  and row.get("commitment") == assignment["commitment"]]
        require(len(claims) == 1, "Job lacks its unique service commitment")
        claim = claims[0]
        for key in ("citizen", "request", "revision", "origin", "selected_packet"):
            require(claim.get(key) == assignment.get(key), "Claim selection changed before assignment: " + key)
        require(transmission["sequence"] < delivery["sequence"] < claim["sequence"]
                < assignment["sequence"], "Request/commitment/job order is invalid")
        require(any(row.get("citizen") == transmission["sender"]
                    and row.get("request") == transmission["request"]
                    and row["sequence"] < transmission["sequence"] for row in carries),
                "Selected request lacks a carrying option by its sender")
        recipient_link = True
    require(recipient_link, "No recipient selected a physical job using a received request")
    return {"observations": len(observed), "sent": len(sent), "received": len(received),
            "assignments": len(assigned), "transfers": len(completed),
            "request_recipient_job_chain": True}


def setup(rcon):
    for command in (
        "gamerule doMobSpawning false", "gamerule doDaylightCycle false",
        "gamerule doWeatherCycle false", "time set 6000", "weather clear",
        "forceload add 0 0 47 15",
        "fill 0 100 0 44 105 6 minecraft:air",
        "fill 0 100 0 44 100 6 minecraft:stone",
        "fill 0 101 0 44 103 0 minecraft:stone",
        "fill 0 101 6 44 103 6 minecraft:stone",
        "fill 0 101 0 0 103 6 minecraft:stone",
        "fill 44 101 0 44 103 6 minecraft:stone",
        f'setblock {xyz(SOURCE)} minecraft:chest{{Items:[{{Slot:0b,id:"minecraft:wheat",Count:{INITIAL}b}}]}} replace',
        f"setblock {xyz(BUFFER)} minecraft:chest replace",
    ):
        answer = rcon.run(command)
        require(not any(word in answer.lower() for word in
                        ("unknown command", "incorrect argument", "not loaded", "failed")),
                "Fixture setup failed: " + answer)
    for tag, x in (("hb_need_a", 3), ("hb_need_b", 35)):
        rcon.require(f"execute positioned {x} 101 2 run sable spawn", "Sable spawned")
        selector = f"@e[type=minecraft:villager,name=Sable,x={x},y=101,z=2,distance=..4,limit=1,sort=nearest]"
        rcon.require(f"tag {selector} add {tag}", "Added tag")
        rcon.require(f"{COMMAND} enroll @e[tag={tag},limit=1]", "NEED_SERVICES")
    rcon.require(f"{COMMAND} configure-buffer {xyz(BUFFER)} {TARGET}", "NEED_SERVICES")
    rcon.require(f"{COMMAND} configure-source {xyz(SOURCE)}", "NEED_SERVICES")
    return {"source": witness(rcon, SOURCE, INITIAL), "buffer": witness(rcon, BUFFER, 0)}


def run_live(rcon, output):
    result = {"schema": SCHEMA, "status": "running", "origin": "REAL_FORGE",
              "initial_stock": INITIAL, "target": TARGET, "source": list(SOURCE),
              "buffer": list(BUFFER), "planned_citizens": 2,
              "deadline_seconds": DEADLINE_SECONDS, "quiet_seconds": QUIET_SECONDS,
              "policy": "PRIVATE_CONTEXTUAL_SERVICE_RLS_V1",
              "production_claimed": False, "learned_emergence_claimed": False,
              "commit": os.environ.get("HEARTHBOUND_EXPECTED_COMMIT", "UNSPECIFIED")}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    try:
        result["before"] = setup(rcon)
        rcon.require(COMMAND + " start", "NEED_SERVICES")
        started = status(rcon)
        require(started["enabled"] and started["enrolled"] == 2, "Controller did not own both citizens")
        deadline = time.monotonic() + DEADLINE_SECONDS
        while True:
            current = status(rcon)
            require(current["held"] == 0, "An unresolved physical job was held")
            require(current["transfers"] <= TARGET, "Buffer oversupplied")
            if current["transfers"] == TARGET:
                break
            require(time.monotonic() < deadline, "Declared live deadline elapsed without complete service")
            time.sleep(0.5)
        result["after"] = {"source": witness(rcon, SOURCE, INITIAL - TARGET),
                           "buffer": witness(rcon, BUFFER, TARGET)}
        assigned_at_target = current["assigned"]
        quiet_end = time.monotonic() + QUIET_SECONDS
        while time.monotonic() < quiet_end:
            time.sleep(0.5)
            current = status(rcon)
            require(current["assigned"] == assigned_at_target and current["transfers"] == TARGET,
                    "A new material job started after the buffer target was met")
            require(current["held"] == 0, "Quiet window hid a held job")
        result["natural_closure_quiet"] = {"seconds": QUIET_SECONDS,
                                            "new_assignments": 0, "new_transfers": 0}
        # Explicit operator configuration withdrawal is separately identified.
        rcon.require(f"{COMMAND} set-target {xyz(BUFFER)} 0", "NEED_SERVICES")
        rcon.require(COMMAND + " stop", "NEED_SERVICES")
        terminal = status(rcon)
        require(not terminal["enabled"] and terminal["held"] == 0
                and terminal["active_commitments"] == 0, "Controller did not stop cleanly")
        result["terminal_inventories"] = {
            "source": witness(rcon, SOURCE, INITIAL - TARGET),
            "buffer": witness(rcon, BUFFER, TARGET)}
        rcon.require("hearthboundclaims count", "Active source claims in this dimension: 0")
        result["records"] = records(rcon, terminal["records_total"])
        result["chain"] = validate_chain(result["records"])
        result["terminal"] = terminal
        result["physical_inventory_witnessed"] = True
        result["status"] = "passed_live_cycle"
        rcon.require("save-all flush", "Saved the game")
        output.write_text(json.dumps(result, indent=2) + "\n")
        print("NEED_SERVICE_FORGE_CYCLE_PASS physical_transfers=2 "
              "recipient_request_chain=true natural_target_closure=true production_claimed=false", flush=True)
        rcon.stop_server()
    except Exception as failure:
        result.update(status="failed", error=type(failure).__name__ + ": " + str(failure))
        output.write_text(json.dumps(result, indent=2) + "\n")
        raise


def verify_restart(rcon, output):
    result = json.loads(output.read_text())
    require(result.get("schema") == SCHEMA and result.get("status") == "passed_live_cycle",
            "No valid pre-restart live result")
    current = status(rcon)
    require(not current["enabled"], "Service controller automatically re-enabled after restart")
    require(current["enrolled"] == 2 and current["transfers"] == TARGET,
            "Persisted membership/completion history changed")
    require(current["active_commitments"] == current["held"] == 0,
            "Completed work restored as an unresolved commitment")
    require(current["assigned"] == result["terminal"]["assigned"]
            and current["cost_updates"] == result["terminal"]["cost_updates"],
            "Persisted assignment or learning counters changed")
    prefix = records(rcon, result["terminal"]["records_total"])
    require(prefix == result["records"], "Stopped request/job/receipt history changed across restart")
    prior = current["assigned"]
    time.sleep(QUIET_SECONDS)
    after = status(rcon)
    require(not after["enabled"] and after["assigned"] == prior and after["transfers"] == TARGET
            and after["active_commitments"] == after["held"] == 0
            and after["cost_updates"] == current["cost_updates"],
            "Stopped restart replayed service work")
    result["restart"] = {"status": after, "source": witness(rcon, SOURCE, INITIAL - TARGET),
                          "buffer": witness(rcon, BUFFER, TARGET),
                          "unresolved_job_restart_tested": False}
    rcon.require("hearthboundclaims count", "Active source claims in this dimension: 0")
    result["status"] = "passed_cycle_and_clean_restart"
    output.write_text(json.dumps(result, indent=2) + "\n")
    print("NEED_SERVICE_FORGE_ACCEPTANCE_PASS real_inventory=true typed_request=true "
          "persistent_service=true clean_stopped_restart=true production_claimed=false "
          "learned_emergence_claimed=false", flush=True)
    rcon.stop_server()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("live", "restart"), required=True)
    parser.add_argument("--output", type=Path, default=Path("run/need-service-acceptance.json"))
    args = parser.parse_args()
    with connection(os.environ["HEARTHBOUND_RCON_PASSWORD"]) as rcon:
        (run_live if args.phase == "live" else verify_restart)(rcon, args.output)


if __name__ == "__main__":
    main()
