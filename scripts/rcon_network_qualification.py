#!/usr/bin/env python3
"""Explicit six-arm qualification collector and physical evidence validator.

Transport/native-witness helpers are reused unchanged. Physical/job/lifecycle
checks are adapted from rcon_private_communication_trial.py at 74763d7c, with
an explicit qualification contract; no evidence is relabelled as a legacy arm.
"""
import json
import ast
import math
import re
import time
from collections import Counter
from network_qualification_protocol import (
    ARMS, BLOCK_ID, CADENCE_TICKS, DESIGN_SHA256, DESTINATION, DIMENSION,
    EDGES, HORIZON_TICKS, INITIAL_STOCK, POLICY_SEED, POSITIONS,
    RUNTIME_SCHEMA, SLOT_TO_SEAT, SOURCES, WALL_GUARD_SECONDS,
    actor_uuid, initial_manifest as matched_manifest,
    parse_json,
)
from rcon_private_communication_trial import (
    SETUP_COMMANDS, actor_witness, communication_audit, communication_snapshot,
    connection, inventories, packed, require, source_key, uuid, uuid_ints,
    validate_setup_response, xyz,
)
from network_qualification_native import inbox_witness, replay_inboxes, validate_inbox_witness

MARKER = "COMMUNICATION_NETWORK_TRIAL_V1 "
COMMAND = "hearthbound-communication-trial"


def trial_id(arm):
    require(arm in ARMS, "Unknown network qualification arm")
    return "qual-" + arm.lower().replace("_", "-")


NETWORK_CONTEXT = {"world", "episode", "arm", "block_id", "trial_id", "design_sha256", "qualification_only"}
RECORD_COMMON = NETWORK_CONTEXT | {"kind", "tick", "relative_tick", "slot", "citizen", "sequence", "round", "physical_seat"}
SEND_FIELDS = {"recipient_slot", "recipient_seat", "recipient", "permission_edge", "route", "edge_allowed",
               "edge_decision", "route_semantics", "charged_send_budget", "result", "attempt_id", "source",
               "source_observation_owner", "observed_tick", "source_revision", "claimed_wheat", "source_state",
               "observation_world", "observation_episode"}
AUDIT_FIELDS = NETWORK_CONTEXT | {"schema", "kind", "dimension", "read_only", "policy_seed", "horizon_ticks",
    "status", "actor_count", "start_tick", "end_tick", "observed_tick", "elapsed_ticks", "rounds", "records_total",
    "record_capacity_denials", "errors", "destination", "cadence_ticks", "max_records", "causal_benefit_established",
    "slot_to_seat", "undirected_permission_edges", "transport_enabled", "reports_exposed_to_decisions"}
COUNTERS = {"idle_opportunities", "motor_ticks", "near_probes", "near_inspections", "outer_probes", "outer_inspections",
            "rechecks", "assignment_attempts", "assignments", "completed_jobs", "send_attempts", "report_reads",
            "motor_elapsed_ns", "discovery_elapsed_ns", "communication_elapsed_ns", "decision_elapsed_ns"}
CAPS = {"near_probes", "near_inspections", "outer_probes", "outer_inspections", "rechecks", "assignment_attempts", "send_attempts"}


def validate_network_context(row, arm, world, episode):
    require(row["arm"] == arm and row["world"] == world and row["episode"] == episode
            and row["block_id"] == BLOCK_ID and row["trial_id"] == trial_id(arm)
            and row["design_sha256"] == DESIGN_SHA256 and row["qualification_only"] is True,
            "Network record changed qualification scope")


def validate_network_contract(data, seed, arm):
    require(arm in ARMS, "Unknown network arm")
    final = data["final"]
    world, episode = uuid(final["world"]), uuid(final["episode"])
    for audit in [data["configured"], data["start"], final, data["final_after_export"], *data.get("polls", [])]:
        require(set(audit) == AUDIT_FIELDS, "Network audit closed schema changed")
        validate_network_context(audit, arm, world, episode)
        require(audit["schema"] == RUNTIME_SCHEMA and audit["kind"] == "audit" and audit["read_only"] is True
                and audit["slot_to_seat"] == list(SLOT_TO_SEAT)
                and audit["undirected_permission_edges"] == EDGES[arm]
                and audit["transport_enabled"] is (arm != "NO_MESSAGES")
                and audit["reports_exposed_to_decisions"] is (arm not in ("NO_MESSAGES", "DIRECT_UNREAD"))
                and audit["policy_seed"] == POLICY_SEED, "Network permission/configuration mismatch")
    for actors in (data["actors_before"], data["actors_after"]):
        for slot, actor in enumerate(actors):
            require(actor["physical_seat"] == SLOT_TO_SEAT[slot]
                    and set(actor["counters"]) == COUNTERS and set(actor["max_per_round"]) == CAPS,
                    "Actor seat or cost schema changed")
    own = {slot: {} for slot in range(4)}
    opportunities, sends = [], []
    phase_order = []
    attempts = {row["id"]: row for row in data["communication"]["attempts"]}
    require(len(attempts) == len(data["communication"]["attempts"]), "Duplicate native attempt ID")
    for row in data["records"]:
        validate_network_context(row, arm, world, episode)
        slot, round_number = row["slot"], row["round"]
        require(type(slot) is int and slot in range(4) and type(round_number) is int
                and 0 <= round_number < 30 and row["relative_tick"] == round_number * 20
                and row["physical_seat"] == SLOT_TO_SEAT[slot]
                and row["citizen"] == actor_uuid(seed, slot), "Network event slot/seat/round mismatch")
        kind = row["kind"]
        phase = (0 if kind == "COMPLETE" else 1 if kind == "OBSERVE" and row.get("phase") != "RECHECK"
                 else 2 if kind in ("SEND", "SEND_OPPORTUNITY") else 3)
        first = (POLICY_SEED % 4 + round_number % 4) % 4
        phase_order.append((round_number, phase, (slot - first) % 4))
        if kind == "OBSERVE":
            require(set(row) == RECORD_COMMON | {"phase", "source", "observer", "state", "wheat", "reason", "revision"},
                    "Observation closed schema changed")
            if row["state"] in ("AVAILABLE", "EMPTY"):
                own[slot][tuple(row["source"])] = row
            continue
        if kind == "DECISION":
            keys = RECORD_COMMON | {"decision", "report_inputs", "private_source_candidates", "claimed_candidates", "result"}
            if row["result"] != "ABSTAIN_NO_AVAILABLE_PRIVATE_SOURCE":
                keys |= {"source", "mode", "evidence_observed_tick", "report_id"}
            require(set(row) == keys, "Decision closed schema changed")
            require(type(row["private_source_candidates"]) is int and 0 <= row["private_source_candidates"] <= 16
                    and type(row["claimed_candidates"]) is int and 0 <= row["claimed_candidates"] <= row["private_source_candidates"],
                    "Private candidate menu bound changed")
            if arm in ("NO_MESSAGES", "DIRECT_UNREAD"):
                require(row["report_inputs"] == 0 and row.get("mode") != "REPORT_CUED_DIRECT_RECHECK",
                        "Policy-inaccessible reports entered a decision")
            continue
        if kind == "ASSIGNED":
            require(set(row) == RECORD_COMMON | {"job", "decision", "source", "destination", "assigned_tick", "mode", "report_id"},
                    "Assignment closed schema changed")
            continue
        if kind == "COMPLETE":
            require(set(row) == RECORD_COMMON | {"job", "source", "destination", "assigned_tick", "delivered_tick", "wheat", "witness"},
                    "Completion closed schema changed")
            continue
        require(kind in ("SEND", "SEND_OPPORTUNITY") and set(row) == RECORD_COMMON | SEND_FIELDS,
                "Unknown network event or send closed schema")
        peer = (slot + 1 + round_number % 3) % 4
        edge = sorted((slot, peer)); allowed = edge in EDGES[arm]
        require(row["recipient_slot"] == peer and row["recipient_seat"] == SLOT_TO_SEAT[peer]
                and row["recipient"] == actor_uuid(seed, peer)
                and row["permission_edge"] == edge and row["edge_allowed"] is allowed
                and row["route"] == [row["citizen"], row["recipient"]],
                "Recipient rotation/permission/one-hop route changed")
        opportunities.append((round_number, slot))
        fresh = sorted((observation for observation in own[slot].values()
                        if 0 <= row["tick"] - observation["tick"] <= 40), key=lambda item: tuple(item["source"]))
        if not fresh:
            require(kind == "SEND_OPPORTUNITY" and row["charged_send_budget"] == 0
                    and row["result"] == "NO_ELIGIBLE_DIRECT_EVIDENCE"
                    and row["edge_decision"] == "NOT_ATTEMPTED_NO_PAYLOAD"
                    and row["route_semantics"] == "PROPOSED_DIRECT_RECIPIENT"
                    and all(row[key] is None for key in ("attempt_id", "source", "source_observation_owner", "observed_tick",
                              "source_revision", "claimed_wheat", "source_state", "observation_world", "observation_episode")),
                    "Empty-payload opportunity fabricated evidence or consumed a send")
            continue
        require(kind == "SEND" and row["charged_send_budget"] == 1
                and row["route_semantics"] == "ATTEMPTED_DIRECT_RECIPIENT", "Available payload did not use one bounded attempt")
        evidence = fresh[round_number % len(fresh)]
        require(row["source"] == evidence["source"] and row["observed_tick"] == evidence["tick"]
                and row["source_revision"] == evidence["revision"] and row["claimed_wheat"] == evidence["wheat"]
                and row["source_state"] == evidence["state"] and row["source_observation_owner"] == row["citizen"]
                and row["observation_world"] == world and row["observation_episode"] == episode,
                "Send payload is not the selected own direct observation")
        permission = "NETWORK_DISABLED" if arm == "NO_MESSAGES" else "ALLOWED" if allowed else "TOPOLOGY_BLOCKED"
        require(row["edge_decision"] == permission and uuid(row["attempt_id"]) in attempts, "Permission/attempt binding missing")
        attempt = attempts[row["attempt_id"]]
        require(attempt["sender"] == row["citizen"] and attempt["recipient"] == row["recipient"]
                and attempt["tick"] == row["tick"] and attempt["source"] == source_key(row["source"]),
                "Exact native attempt changed sender/recipient/tick/source")
        if permission != "ALLOWED":
            require(attempt["outcome"] == "REJECTED" and attempt["reason"] == permission
                    and row["result"] == "REJECTED_" + permission, "Forbidden edge reached transport")
        elif attempt["outcome"] == "REJECTED":
            require(attempt["reason"] not in ("NETWORK_DISABLED", "TOPOLOGY_BLOCKED")
                    and row["result"] == "KNOWLEDGE_SHARE ABSTAIN reason=" + attempt["reason"] + " action_authorized=false",
                    "Allowed transport rejection changed")
        elif attempt["outcome"] == "DUPLICATE":
            require(row["result"] == "KNOWLEDGE_SHARE status=DUPLICATE action_authorized=false", "Duplicate transport result changed")
        else:
            require(attempt["outcome"] == "DELIVERED" and row["result"].startswith("KNOWLEDGE_SHARE status=DELIVERED "),
                    "Transport outcome changed")
        sends.append(row)
    expected = [(round_number, (POLICY_SEED % 4 + round_number % 4 + offset) % 4)
                for round_number in range(30) for offset in range(4)]
    require(opportunities == expected, "Communication round opportunities missing, duplicated or reordered")
    require(phase_order == sorted(phase_order), "Motor/discovery/communication/decision phase or actor priority changed")
    require([row["attempt_id"] for row in sends] == [row["id"] for row in data["communication"]["attempts"]],
            "Native attempts differ from ordered charged sends")
    citizens = [actor_uuid(seed, slot) for slot in range(4)]
    for key in ("native_inboxes_before", "native_inboxes_after", "native_inboxes_after_export"):
        require(len(data[key]) == 4 and [row["citizen"] for row in data[key]] == citizens, "Native inbox roster changed")
        for witness in data[key]:
            validate_inbox_witness(witness)
    require(all(row["status"] == "ABSENT_AT_NATIVE_PROBE" for row in data["native_inboxes_before"]),
            "Qualification started with preexisting inbox state")
    expected_inboxes, lifecycle = replay_inboxes(data["communication"], citizens, final["end_tick"])
    require(data["native_inboxes_after"] == data["native_inboxes_after_export"], "Native inbox changed after freeze")
    for witness in data["native_inboxes_after"]:
        citizen = witness["citizen"]
        received = any(message["recipient"] == citizen for message in data["communication"]["messages"])
        require(witness["entries"] == expected_inboxes[citizen]
                and (witness["status"] == "OBSERVED_NATIVE_INBOX") == received,
                "Native recipient inbox differs from actual delivery/pruning/eviction history")
    require(len(data["native_actors_after_export"]) == 4, "Missing repeated native motor witnesses")
    for before, after in zip(data["native_actors_after"], data["native_actors_after_export"]):
        require(all(before[key] == after[key] for key in ("citizen", "no_ai", "cargo_wheat", "motor")),
                "Scored native cargo/job authority changed after freeze")
    return {"communication_opportunities": len(opportunities), "charged_send_attempts": len(sends),
            "no_payload_opportunities": 120 - len(sends),
            "network_disabled_attempts": sum(row["edge_decision"] == "NETWORK_DISABLED" for row in sends),
            "topology_blocked_attempts": sum(row["edge_decision"] == "TOPOLOGY_BLOCKED" for row in sends),
            "allowed_transport_attempts": sum(row["edge_decision"] == "ALLOWED" for row in sends),
            "native_inboxes_verified": True, "inbox_lifecycle_by_recipient": lifecycle,
            "permission_edges": EDGES[arm], "slot_to_seat": list(SLOT_TO_SEAT)}


def runtime(rcon, suffix="audit"):
    response = rcon.require(f"{COMMAND} {suffix}", MARKER)
    parsed = parse_json(response.split(MARKER, 1)[1])
    require(parsed["schema"] == RUNTIME_SCHEMA, "Unexpected runtime schema")
    return parsed


def pages(rcon, kind, scope=None):
    result, total = [], None
    expected_scope = ({key: scope[key] for key in ("world", "episode", "dimension")}
                      if scope is not None else None)
    while total is None or len(result) < total:
        require(len(result) <= 4096, "Unbounded runtime export")
        page = runtime(rcon, f"{kind} {len(result)}")
        require(set(page) == NETWORK_CONTEXT | {"schema", "kind", "dimension", "read_only", "offset", "total", "records", "next_offset"},
                "Network page closed schema changed")
        validate_network_context(page, scope["arm"] if scope is not None else page["arm"], page["world"], page["episode"])
        require(page["kind"] == kind and page["offset"] == len(result),
                "Runtime pagination identity mismatch")
        require(page["read_only"] is True, "Runtime export is not read-only")
        actual_scope = {key: page[key] for key in ("world", "episode", "dimension")}
        if expected_scope is None:
            expected_scope = actual_scope
        require(actual_scope == expected_scope, "Runtime page changed world/session/dimension")
        if total is not None:
            require(page["total"] == total, "Runtime history changed during export")
        total = page["total"]
        require(type(total) is int and 0 <= total <= 4096, "Invalid runtime record total")
        rows = page["records"]
        require(isinstance(rows, list), "Invalid runtime records")
        if not rows:
            require(len(result) == total, "Truncated runtime export")
            break
        result.extend(rows)
        require(len(result) <= total, "Runtime export exceeded total")
        expected_next = len(result) if len(result) < total else None
        require(page["next_offset"] == expected_next, "Invalid runtime next offset")
    return result


def setup(rcon, seed, arm, data):
    require(arm in ARMS, "Unknown communication arm")
    data["declared_initial_manifest"] = matched_manifest(seed)
    data["communication_before"] = communication_audit(rcon)
    require(data["communication_before"]["messages"] == 0
            and data["communication_before"]["send_attempts"] == 0
            and data["communication_before"]["events"] == 0,
            "Preexisting communication evidence in supposedly fresh world")
    data["setup_commands"] = []
    for command in SETUP_COMMANDS:
        response = rcon.run(command)
        validate_setup_response(command, response)
        data["setup_commands"].append({"command": command, "response": response})
    for position, stock in zip(SOURCES, INITIAL_STOCK):
        rcon.require(f'setblock {xyz(position)} minecraft:chest{{Items:[{{Slot:0b,'
                     f'id:"minecraft:wheat",Count:{stock}b}}]}} replace', "Changed the block")
    rcon.require(f"setblock {xyz(DESTINATION)} minecraft:chest replace", "Changed the block")
    data["configured"] = runtime(rcon, f"configure-network {arm} {POLICY_SEED} {HORIZON_TICKS} {xyz(DESTINATION)} 2031 {BLOCK_ID} {trial_id(arm)}")
    for slot, position in enumerate(POSITIONS):
        citizen = actor_uuid(seed, slot)
        ints = ",".join(str(value) for value in uuid_ints(citizen))
        nbt = ('{UUID:[I;' + ints + '],CustomName:\'{"text":"TrialWorker' + str(slot)
               + '"}\',PersistenceRequired:1b,NoAI:1b,Rotation:[0f,0f],'
               'ForgeData:{"hearthbound.sable":1b}}')
        rcon.require(f"summon minecraft:villager {xyz(position)} {nbt}", "Summoned new")
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            if "Test passed, count: 1" in rcon.run(f"execute if entity {citizen}"):
                break
            time.sleep(0.1)
        else:
            raise TimeoutError("Original fixture citizen did not load")
        runtime(rcon, f"enroll {slot} {citizen}")
    data["actors_before"] = pages(rcon, "actors", data["configured"])
    data["inventories_before"] = inventories(rcon)
    data["native_actors_before"] = [actor_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    data["native_inboxes_before"] = [inbox_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    data["settings_before"] = {}
    for name, expected in matched_manifest(seed)["initial_game_rules"].items():
        response = rcon.run(f"gamerule {name}")
        value = str(expected).lower()
        require(response.rstrip().endswith("is currently set to: " + value), "Initial gamerule differs from declaration")
        data["settings_before"][name] = {"value": expected, "raw": response}
    response = rcon.run("time query daytime")
    require(re.search(r"\b6000\s*$", response) is not None, "Initial daytime differs from declaration")
    data["settings_before"]["daytime"] = {"value": 6000, "raw": response}
    require([row["wheat"] for row in data["inventories_before"]["sources"]] == list(INITIAL_STOCK)
            and data["inventories_before"]["destination"]["wheat"] == 0,
            "Initial inventories differ from planned resources")
    require(len(data["actors_before"]) == 4, "Four actors were not enrolled")
    for slot, (actor, native) in enumerate(zip(data["actors_before"], data["native_actors_before"])):
        require(actor["slot"] == slot and actor["citizen"] == actor_uuid(seed, slot)
                and actor["initial_position"] == list(POSITIONS[slot])
                and native["position"] == list(POSITIONS[slot])
                and native["rotation"] == [0.0, 0.0] and native["cargo_wheat"] == 0,
                "Observed actor initial state differs from matched manifest")


def run_trial(rcon, seed, arm, data):
    setup(rcon, seed, arm, data)
    start = time.monotonic()
    data["start"] = runtime(rcon, "start")
    data["active_interventions_after_start"] = 0
    deadline = start + WALL_GUARD_SECONDS
    data["polls"] = []
    while time.monotonic() < deadline:
        current = runtime(rcon)
        data["polls"].append(current)
        if current["status"] == "COMPLETE":
            break
        require(current["status"] in ("SCHEDULED", "RUNNING"), "Runtime entered an error state")
        time.sleep(1)
    else:
        raise TimeoutError("Fixed game-tick horizon did not finish within wall-clock guard")
    data["horizon_wall_seconds"] = time.monotonic() - start
    data["final"] = current
    data["actors_after"] = pages(rcon, "actors", current)
    data["records"] = pages(rcon, "records", current)
    data["communication"] = communication_snapshot(rcon)
    data["inventories_after"] = inventories(rcon)
    data["native_actors_after"] = [actor_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    data["native_inboxes_after"] = [inbox_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    data["claims_after_raw"] = rcon.require("hearthboundclaims count", "Active source claims")
    match = re.search(r"Active source claims in this dimension: (\d+)", data["claims_after_raw"])
    require(match is not None, "Missing source claim count")
    data["claims_after"] = int(match[1])
    data["final_after_export"] = runtime(rcon)
    data["inventories_after_export"] = inventories(rcon)
    data["native_inboxes_after_export"] = [inbox_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    data["native_actors_after_export"] = [actor_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    require(data["inventories_after_export"] == data["inventories_after"],
            "Physical inventories changed after fixed horizon")
    data["metrics"] = validate_trial(data, seed, arm)
    print("NETWORK_QUALIFICATION_PHYSICAL_PASS " + json.dumps(data["metrics"], sort_keys=True), flush=True)
    return data


def validate_trial(data, seed, arm):
    """Validate the fixed horizon, budget, provenance, and physical conservation."""
    return validate_runtime_evidence(data, seed, arm)


class TranscriptRcon:
    """Replay complete recorded requests without a socket or world mutation."""
    def __init__(self, text):
        self.rows, self.offset = [], 0
        prefix = "PRIVATE_COMMUNICATION_RCON command="
        for line in text.splitlines():
            if not line.startswith(prefix):
                continue
            command, response = line[len(prefix):].split(" response=", 1)
            command, response = ast.literal_eval(command), ast.literal_eval(response)
            require(isinstance(command, str) and isinstance(response, str), "Invalid transcript row")
            self.rows.append((command, response))
        require(0 < len(self.rows) <= 10000, "Missing or oversized qualification transcript")

    def run(self, command):
        require(self.offset < len(self.rows), "Truncated native transcript")
        actual, response = self.rows[self.offset]
        require(actual == command, "Unexpected or intervening native command: " + actual)
        self.offset += 1
        return response

    def require(self, command, expected):
        response = self.run(command)
        require(expected.lower() in response.lower(), "Native transcript command failed")
        return response


def replay_transcript(text, data, seed, arm):
    """Re-read all setup, runtime, and physical exports from their original replies."""
    rcon, observed = TranscriptRcon(text), {}
    setup(rcon, seed, arm, observed)
    observed["start"] = runtime(rcon, "start")
    observed["polls"] = [runtime(rcon) for _ in data["polls"]]
    require(observed["polls"] and observed["polls"][-1]["status"] == "COMPLETE",
            "Transcript never reached the fixed horizon")
    observed["final"] = observed["polls"][-1]
    observed["actors_after"] = pages(rcon, "actors", observed["final"])
    observed["records"] = pages(rcon, "records", observed["final"])
    observed["communication"] = communication_snapshot(rcon)
    observed["inventories_after"] = inventories(rcon)
    observed["native_actors_after"] = [actor_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    observed["native_inboxes_after"] = [inbox_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    observed["claims_after_raw"] = rcon.require("hearthboundclaims count", "Active source claims")
    match = re.search(r"Active source claims in this dimension: (\d+)", observed["claims_after_raw"])
    require(match is not None, "Missing native claim count")
    observed["claims_after"] = int(match[1])
    observed["final_after_export"] = runtime(rcon)
    observed["inventories_after_export"] = inventories(rcon)
    observed["native_inboxes_after_export"] = [inbox_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    observed["native_actors_after_export"] = [actor_witness(rcon, actor_uuid(seed, slot)) for slot in range(4)]
    require(all(data.get(key) == value for key, value in observed.items()),
            "Qualification result differs from original native/runtime transcript")
    remaining = rcon.rows[rcon.offset:]
    require(remaining and remaining[0][0] == "save-all flush" and "Saved the game" in remaining[0][1]
            and (len(remaining) == 1 or len(remaining) == 2
                 and remaining[1][0] == "stop" and "Stopping the server" in remaining[1][1]),
            "Unrecorded intervention or missing final save in transcript")
    return {"rcon_requests_replayed": rcon.offset, "remaining_requests": len(remaining),
            "exact_setup_and_evidence_export_replayed": True}


def validate_initial(data, seed, arm):
    manifest = matched_manifest(seed)
    require(data["declared_initial_manifest"] == manifest, "Initial contract mismatch")
    require([row["command"] for row in data["setup_commands"]] == list(SETUP_COMMANDS), "Arena setup contract changed")
    for row in data["setup_commands"]:
        validate_setup_response(row["command"], row["response"])
    configured = data["configured"]
    require(configured["schema"] == RUNTIME_SCHEMA and configured["status"] == "CONFIGURED"
            and configured["arm"] == arm and configured["policy_seed"] == POLICY_SEED
            and configured["horizon_ticks"] == HORIZON_TICKS and configured["actor_count"] == 0
            and configured["rounds"] == configured["records_total"] == 0
            and configured["destination"] == list(DESTINATION), "Initial runtime configuration changed")
    require(len(data["actors_before"]) == len(data["native_actors_before"]) == 4, "Initial actor cohort incomplete")
    for slot, (actor, native) in enumerate(zip(data["actors_before"], data["native_actors_before"])):
        require(actor["slot"] == slot and actor["citizen"] == native["citizen"] == actor_uuid(seed, slot)
                and actor["initial_position"] == actor["current_position"] == native["position"] == list(POSITIONS[slot])
                and actor["initial_no_ai"] is True and actor["no_ai"] is True and native["no_ai"] is True
                and native["rotation"] == [0.0, 0.0]
                and actor["cargo_wheat"] == native["cargo_wheat"] == 0
                and actor["private_sources"] == 0 and actor["phase"] is None
                and actor["current_job"] is None and native["motor"] is None
                and actor["active"] is False and actor["present"] is True
                and actor["policy_id"] == manifest["policy_id"]
                and all(value == 0 for value in actor["counters"].values())
                and all(value == 0 for value in actor["max_per_round"].values()),
                "Observed initial actor state differs from matched conditions")
    require([row["wheat"] for row in data["inventories_before"]["sources"]] == list(INITIAL_STOCK)
            and data["inventories_before"]["destination"]["wheat"] == 0, "Initial physical inventory mismatch")
    expected_settings = dict(manifest["initial_game_rules"], daytime=6000)
    require(set(data["settings_before"]) == set(expected_settings), "Initial setting evidence incomplete")
    for key, expected in expected_settings.items():
        entry = data["settings_before"][key]
        require(entry["value"] == expected, "Initial setting value mismatch")
        if key == "daytime":
            require(re.search(r"\b6000\s*$", entry["raw"]) is not None, "Initial daytime witness mismatch")
        else:
            require(entry["raw"].rstrip().endswith("is currently set to: " + str(expected).lower()),
                    "Initial gamerule witness mismatch")
    initial = data["communication_before"]
    require(initial["world"] == configured["world"] and initial["episode"] == configured["episode"]
            and all(initial[key] == 0 for key in ("messages", "events", "send_attempts", "read", "selected", "assigned", "physical_completed")),
            "World did not begin with empty communication history")
    started = data["start"]
    require(started["status"] == "SCHEDULED" and started["actor_count"] == 4
            and started["world"] == configured["world"] and started["episode"] == configured["episode"]
            and started["start_tick"] - started["observed_tick"] == 20
            and started["end_tick"] - started["start_tick"] == HORIZON_TICKS
            and started["rounds"] == started["records_total"] == 0, "Trial start was not synchronized after readiness")


def validate_runtime_evidence(data, seed, arm):
    validate_initial(data, seed, arm)
    network = validate_network_contract(data, seed, arm)
    final = data["final"]
    require(data["declared_initial_manifest"] == matched_manifest(seed), "Initial contract mismatch")
    require(final["schema"] == RUNTIME_SCHEMA and final["status"] == "COMPLETE"
            and final["arm"] == arm and final["policy_seed"] == POLICY_SEED
            and final["dimension"] == DIMENSION and final["actor_count"] == 4
            and final["destination"] == list(DESTINATION), "Runtime identity/configuration mismatch")
    uuid(final["world"]); uuid(final["episode"])
    require(final["world"] == data["configured"]["world"]
            and final["episode"] == data["configured"]["episode"]
            and final["start_tick"] == data["start"]["start_tick"]
            and final["end_tick"] == data["start"]["end_tick"], "Trial changed scope or horizon after start")
    require(final["horizon_ticks"] == HORIZON_TICKS and final["cadence_ticks"] == CADENCE_TICKS
            and final["end_tick"] - final["start_tick"] == HORIZON_TICKS
            and final["elapsed_ticks"] == HORIZON_TICKS
            and final["rounds"] == HORIZON_TICKS // CADENCE_TICKS
            and final["observed_tick"] >= final["end_tick"], "Incomplete or altered game-tick horizon")
    require(final["record_capacity_denials"] == 0 and final["errors"] == []
            and final["causal_benefit_established"] is False, "Runtime evidence lost or error state retained")
    stable = lambda audit: {key: value for key, value in audit.items() if key != "observed_tick"}
    require(stable(data["final_after_export"]) == stable(final), "Runtime changed during frozen export")
    require(data["active_interventions_after_start"] == 0, "Active operator intervention during horizon")
    require(type(data["horizon_wall_seconds"]) in (int, float)
            and math.isfinite(data["horizon_wall_seconds"])
            and 0 <= data["horizon_wall_seconds"] < WALL_GUARD_SECONDS, "Wall guard exceeded")
    actors = data["actors_after"]
    records = data["records"]
    require(len(actors) == 4 and len(data["native_actors_after"]) == 4, "Missing final actors")
    require(len(records) == final["records_total"] <= final["max_records"] == 4096,
            "Incomplete runtime record export")
    require([row["sequence"] for row in records] == list(range(1, len(records) + 1)),
            "Runtime event sequence has gaps or duplicates")
    require([row["tick"] for row in records] == sorted(row["tick"] for row in records),
            "Runtime event clock regressed")
    by_kind = {kind: [] for kind in ("OBSERVE", "SEND", "SEND_OPPORTUNITY", "DECISION", "ASSIGNED", "COMPLETE")}
    for row in records:
        require(row["kind"] in by_kind and row["slot"] in range(4)
                and row["citizen"] == actor_uuid(seed, row["slot"]), "Unknown runtime event or actor")
        require(final["start_tick"] <= row["tick"] < final["end_tick"]
                and row["relative_tick"] == row["tick"] - final["start_tick"]
                and row["relative_tick"] % CADENCE_TICKS == 0, "Event outside scheduled opportunity")
        by_kind[row["kind"]].append(row)
    decisions = {uuid(row["decision"]): row for row in by_kind["DECISION"]}
    assignments = {uuid(row["job"]): row for row in by_kind["ASSIGNED"]}
    completions = {uuid(row["job"]): row for row in by_kind["COMPLETE"]}
    require(len(decisions) == len(by_kind["DECISION"]) and len(assignments) == len(by_kind["ASSIGNED"])
            and len(completions) == len(by_kind["COMPLETE"]), "Duplicate decision/job/completion identity")
    for observation in by_kind["OBSERVE"]:
        require(observation["phase"] in ("NEAR", "OUTER", "RECHECK")
                and tuple(observation["source"]) in SOURCES, "Unexpected policy-facing source or sensor")
        observer, source = observation["observer"], observation["source"]
        require(len(observer) == 3 and all(type(value) in (int, float) and math.isfinite(value) for value in observer),
                "Invalid observation position")
        require(sum((source[i] + .5 - observer[i])**2 for i in range(3)) <= 16**2,
                "Out-of-range policy observation")
        block = [math.floor(value) for value in observer]
        near = abs(source[0] - block[0]) <= 2 and abs(source[1] - block[1]) <= 1 and abs(source[2] - block[2]) <= 2
        if observation["phase"] == "NEAR":
            require(near, "Near sensor escaped near geometry")
        elif observation["phase"] == "OUTER":
            require(not near and abs(source[1] - block[1]) <= 1, "Outer sensor escaped current geometry")
        require(observation["state"] in ("AVAILABLE", "EMPTY", "UNKNOWN")
                and type(observation["wheat"]) is int and 0 <= observation["wheat"] <= 2,
                "Invalid source observation state")
        if observation["state"] == "AVAILABLE":
            require(observation["wheat"] > 0 and observation["reason"] == "OBSERVED"
                    and type(observation["revision"]) is int and observation["revision"] > 0,
                    "Positive observation missing direct witness")
        elif observation["state"] == "EMPTY":
            require(observation["wheat"] == 0 and observation["reason"] == "OBSERVED"
                    and type(observation["revision"]) is int and observation["revision"] > 0,
                    "Empty observation missing direct witness")
        else:
            require(observation["wheat"] == 0 and observation["revision"] is None,
                    "Unknown observation created positive knowledge")
    for decision in decisions.values():
        require(decision["result"] in ("ABSTAIN_NO_AVAILABLE_PRIVATE_SOURCE", "CUE_RECHECK_NOT_AVAILABLE", "SELECTED_FRESH_RECHECK")
                and type(decision["report_inputs"]) is int and 0 <= decision["report_inputs"] <= 16,
                "Invalid private decision result")
        if decision["result"] == "ABSTAIN_NO_AVAILABLE_PRIVATE_SOURCE":
            require("source" not in decision, "Abstention unexpectedly selected a source")
            continue
        require(tuple(decision["source"]) in SOURCES
                and 0 <= decision["tick"] - decision["evidence_observed_tick"] <= 200
                and decision["mode"] in ("DIRECT_MEMORY_RECHECK", "REPORT_CUED_DIRECT_RECHECK"),
                "Decision used an invalid or expired private cue")
        rechecks = [row for row in by_kind["OBSERVE"] if row["phase"] == "RECHECK"
                    and row["citizen"] == decision["citizen"] and row["tick"] == decision["tick"]
                    and row["source"] == decision["source"] and row["sequence"] < decision["sequence"]]
        require(len(rechecks) == 1, "Selected cue lacks exactly one actual direct recheck")
        if decision["result"] == "SELECTED_FRESH_RECHECK":
            require(rechecks[0]["state"] == "AVAILABLE", "Assigned source was not currently positive")
        if decision["mode"] == "DIRECT_MEMORY_RECHECK":
            require(decision["report_id"] is None and any(
                row["citizen"] == decision["citizen"] and row["source"] == decision["source"]
                and row["tick"] == decision["evidence_observed_tick"] and row["state"] == "AVAILABLE"
                and row["sequence"] < rechecks[0]["sequence"] for row in by_kind["OBSERVE"]),
                "Direct decision had no own prior source observation")
        else:
            require(isinstance(decision["report_id"], str) and decision["report_inputs"] > 0,
                    "Report cue was not read by policy")
    for job, assigned in assignments.items():
        require(assigned["decision"] in decisions, "Assignment has no actual decision")
        choice = decisions[assigned["decision"]]
        require(choice["result"] == "SELECTED_FRESH_RECHECK"
                and choice["citizen"] == assigned["citizen"]
                and choice["source"] == assigned["source"] and choice["mode"] == assigned["mode"]
                and choice["report_id"] == assigned["report_id"]
                and assigned["destination"] == list(DESTINATION)
                and assigned["assigned_tick"] == assigned["tick"] == choice["tick"]
                and choice["sequence"] < assigned["sequence"], "Assignment changed the selected private decision")
    require(len({row["decision"] for row in assignments.values()}) == len(assignments),
            "One decision issued multiple jobs")
    for job, completed in completions.items():
        require(job in assignments, "Completion lacks observed job assignment")
        assigned = assignments[job]
        require(completed["citizen"] == assigned["citizen"] and completed["source"] == assigned["source"]
                and completed["destination"] == assigned["destination"]
                and completed["assigned_tick"] == assigned["assigned_tick"]
                and assigned["tick"] <= completed["delivered_tick"] == completed["tick"]
                and assigned["sequence"] < completed["sequence"]
                and completed["wheat"] == 1
                and completed["witness"] == "EXECUTOR_INSERTION_RETURNED_NO_REMAINDER",
                "Physical receipt changed job, actor, endpoints, quantity or clock")
    limits = {"near_probes": 75, "near_inspections": 4, "outer_probes": 75,
              "outer_inspections": 4, "rechecks": 1, "assignment_attempts": 1, "send_attempts": 1}
    totals, contributions, inflight = {}, [], []
    for slot, (actor, native) in enumerate(zip(actors, data["native_actors_after"])):
        citizen = actor_uuid(seed, slot)
        require(actor["slot"] == slot and actor["citizen"] == native["citizen"] == citizen
                and actor["initial_position"] == list(POSITIONS[slot]) and actor["initial_no_ai"] is True
                and actor["policy_id"] == "SCRIPTED_PRIVATE_NEAREST_V1"
                and actor["no_ai"] is True and native["no_ai"] is True and actor["present"] is True
                and 0 <= actor["private_sources"] <= 16, "Actor configuration or private memory bound changed")
        counters, maxima = actor["counters"], actor["max_per_round"]
        require(all(type(value) is int and value >= 0 for value in counters.values()), "Invalid actor counter")
        for name, limit in limits.items():
            require(type(maxima[name]) is int and 0 <= maxima[name] <= limit,
                    "Per-round policy budget exceeded: " + name)
            opportunities = final["rounds"] if name == "send_attempts" else counters["idle_opportunities"]
            require(counters[name] <= opportunities * limit, "Cumulative policy budget exceeded: " + name)
        require(counters["idle_opportunities"] <= final["rounds"]
                and counters["motor_ticks"] <= final["rounds"]
                and counters["idle_opportunities"] + counters["motor_ticks"] >= final["rounds"],
                "Missing or extra control opportunities")
        own = lambda kind: [row for row in by_kind[kind] if row["citizen"] == citizen]
        require(counters["idle_opportunities"] == len(own("DECISION"))
                and counters["assignments"] == len(own("ASSIGNED"))
                and counters["assignment_attempts"] == counters["assignments"]
                and counters["completed_jobs"] == len(own("COMPLETE"))
                and counters["send_attempts"] == len(own("SEND")), "Actor counts disagree with actual event ledger")
        for phase, counter in (("NEAR", "near_inspections"), ("OUTER", "outer_inspections"), ("RECHECK", "rechecks")):
            observed = [row for row in own("OBSERVE") if row["phase"] == phase]
            require(counters[counter] == len(observed), "Unaccounted direct sensor call")
            per_tick = {tick: sum(row["tick"] == tick for row in observed) for tick in {row["tick"] for row in observed}}
            require(max(per_tick.values(), default=0) <= limits[counter], "Observed sensor calls exceeded round cap")
        for kind in ("SEND", "DECISION", "ASSIGNED"):
            require(len({row["tick"] for row in own(kind)}) == len(own(kind)), "Extra per-round actor operation")
        require(actor["cargo_wheat"] == native["cargo_wheat"] in (0, 1), "Runtime cargo differs from native entity NBT")
        accepted = own("ASSIGNED")
        if not accepted:
            require(actor["current_job"] is None and actor["phase"] is None and native["motor"] is None
                    and actor["active"] is False and actor["cargo_wheat"] == 0, "Unrecorded physical job")
        else:
            last = accepted[-1]
            motor = native["motor"]
            require(motor is not None and actor["current_job"] == motor["job"] == last["job"]
                    and actor["phase"] == motor["phase"]
                    and motor["source"] == packed(last["source"])
                    and motor["destination"] == packed(DESTINATION)
                    and motor["assignedTick"] == last["assigned_tick"], "Native final job differs from recorded assignment")
            for earlier in accepted[:-1]:
                require(earlier["job"] in completions, "New assignment overwrote unfinished job")
            if last["job"] in completions:
                require(actor["phase"] == 2 and actor["active"] is False and actor["cargo_wheat"] == 0
                        and motor["physicalDeliveredTick"] == completions[last["job"]]["delivered_tick"],
                        "Native completion disagrees with receipt")
            else:
                require(actor["phase"] in (0, 1, 3, 4, 5) and actor["active"] is True,
                        "Unfinished job has impossible motor state")
                inflight.append({"citizen": citizen, "job": last["job"], "source": last["source"],
                                 "phase": actor["phase"], "cargo_wheat": actor["cargo_wheat"]})
        contributions.append({"slot": slot, "citizen": citizen, "delivered_wheat": counters["completed_jobs"]})
        for name, value in counters.items():
            totals[name] = totals.get(name, 0) + value
    before, after = data["inventories_before"], data["inventories_after"]
    require([row["wheat"] for row in before["sources"]] == list(INITIAL_STOCK)
            and before["destination"]["wheat"] == 0, "Initial stock mismatch")
    require(after == data["inventories_after_export"], "Physical state changed after horizon")
    delivered = after["destination"]["wheat"]
    require(type(delivered) is int and 0 <= delivered <= sum(INITIAL_STOCK)
            and delivered == len(completions), "Destination gain disagrees with actual completion receipts")
    for index, source in enumerate(SOURCES):
        remaining = after["sources"][index]["wheat"]
        require(type(remaining) is int and 0 <= remaining <= INITIAL_STOCK[index], "Invalid final source stock")
        known_transfers = sum(tuple(row["source"]) == source for row in completions.values())
        known_cargo = sum(row["cargo_wheat"] for row in inflight if tuple(row["source"]) == source)
        require(INITIAL_STOCK[index] - remaining == known_transfers + known_cargo,
                "Per-source physical conservation or accounting mismatch")
    cargo = sum(row["cargo_wheat"] for row in inflight)
    require(sum(row["wheat"] for row in after["sources"]) + delivered + cargo == sum(INITIAL_STOCK),
            "Physical wheat conservation failed")
    require(data["claims_after"] == len(inflight), "Source claims differ from unfinished physical jobs")
    comm = validate_communication(data["communication"], final, seed, arm, by_kind, decisions, assignments, completions)
    require(totals["send_attempts"] == comm["send_attempts"] and totals["report_reads"] == comm["policy_reads"],
            "Communication cost counters disagree with actual records")
    per_citizen = actor_evidence(data, network, by_kind, assignments, completions)
    delivery_ticks = sorted(row["delivered_tick"] - final["start_tick"] for row in completions.values())
    return {"physical_wheat_delivered": delivered, "source_wheat_remaining": sum(row["wheat"] for row in after["sources"]),
            "cargo_wheat_at_horizon": cargo, "unfinished_jobs": len(inflight), "inflight": inflight,
            "first_delivery_relative_tick": delivery_ticks[0] if delivery_ticks else None,
            "all_four_delivery_relative_tick": delivery_ticks[-1] if delivered == sum(INITIAL_STOCK) else None,
            "all_four_censored_at_tick": None if delivered == sum(INITIAL_STOCK) else HORIZON_TICKS,
            "output_ticks": sum(HORIZON_TICKS - tick for tick in delivery_ticks),
            "game_ticks": HORIZON_TICKS, "horizon_wall_seconds": data["horizon_wall_seconds"],
            "actor_contributions": contributions, "actor_metrics": per_citizen,
            "costs": totals, "communication": comm, "network": network,
            "direct_only_physical_jobs": sum(assignments[job]["mode"] == "DIRECT_MEMORY_RECHECK" for job in completions),
            "communication_win_required": False, "causal_benefit_established": False}


def actor_evidence(data, network, runtime_rows, assignments, completions):
    """Attribute validated costs, denials and complete job history to each citizen."""
    communication = data["communication"]
    rows = []
    for actor in data["actors_after"]:
        citizen = actor["citizen"]
        attempts = [row for row in communication["attempts"] if row["sender"] == citizen]
        sent = [row for row in communication["messages"] if row["sender"] == citizen]
        received = [row for row in communication["messages"] if row["recipient"] == citizen]
        events = [row for row in communication["events"] if row["actor"] == citizen]
        stages = {stage: sum(event["stage"] == stage for event in events)
                  for stage in ("DELIVERED", "READ", "SELECTED", "ASSIGNED", "PHYSICAL_COMPLETED")}
        require(actor["counters"]["report_reads"] == stages["READ"],
                "Actor report-read cost differs from its own actual READ events")
        sends = [row for row in runtime_rows["SEND"] if row["citizen"] == citizen]
        opportunities = sends + [row for row in runtime_rows["SEND_OPPORTUNITY"] if row["citizen"] == citizen]
        own_assignments = [row for row in assignments.values() if row["citizen"] == citizen]
        chains = []
        for assigned in own_assignments:
            job = assigned["job"]
            completed = completions.get(job)
            job_events = [event for event in events if event.get("job_id") == job]
            message_ids = sorted({event["message_id"] for event in job_events})
            chains.append({"job": job, "decision": assigned["decision"], "mode": assigned["mode"],
                           "report_id": assigned["report_id"], "message_ids": message_ids,
                           "source": assigned["source"], "destination": assigned["destination"],
                           "assigned_tick": assigned["assigned_tick"],
                           "status": "PHYSICAL_COMPLETED" if completed else "PENDING_AT_HORIZON",
                           "delivered_tick": completed["delivered_tick"] if completed else None,
                           "wheat_transferred": completed["wheat"] if completed else 0,
                           "native_communication_event_sequences": [event["sequence"] for event in job_events]})
        read_messages = {event["message_id"] for event in events if event["stage"] == "READ"}
        selected_messages = {event["message_id"] for event in events if event["stage"] == "SELECTED"}
        rows.append({"slot": actor["slot"], "physical_seat": actor["physical_seat"], "citizen": citizen,
                     "costs": dict(actor["counters"]), "max_per_round": dict(actor["max_per_round"]),
                     "communication_opportunities": len(opportunities), "charged_send_attempts": len(attempts),
                     "no_payload_opportunities": len(opportunities) - len(attempts),
                     "send_outcomes": {outcome: sum(row["outcome"] == outcome for row in attempts)
                                       for outcome in ("DELIVERED", "DUPLICATE", "REJECTED")},
                     "send_reasons": dict(sorted(Counter(row["reason"] for row in attempts).items())),
                     "rejection_reasons": dict(sorted(Counter(row["reason"] for row in attempts
                                                              if row["outcome"] == "REJECTED").items())),
                     "permission_decisions": {decision: sum(row["edge_decision"] == decision for row in sends)
                                              for decision in ("ALLOWED", "NETWORK_DISABLED", "TOPOLOGY_BLOCKED")},
                     "delivered_sent": len(sent), "delivered_received": len(received),
                     "policy_reads": stages["READ"], "selected_reports": stages["SELECTED"],
                     "report_cued_assignments": stages["ASSIGNED"],
                     "report_cued_physical_jobs": stages["PHYSICAL_COMPLETED"],
                     "direct_only_physical_jobs": sum(row["job"] in completions
                         and row["mode"] == "DIRECT_MEMORY_RECHECK" for row in own_assignments),
                     "physical_jobs_completed": sum(row["job"] in completions for row in own_assignments),
                     "physical_wheat_delivered": sum(completions[row["job"]]["wheat"] for row in own_assignments
                                                      if row["job"] in completions),
                     "never_read_received_messages": len(received) - len(read_messages),
                     "never_selected_received_messages": len(received) - len(selected_messages),
                     "received_messages_expired_by_horizon": sum(message["expires_after_tick"] < data["final"]["end_tick"]
                                                               for message in received),
                     "inbox_lifecycle": dict(network["inbox_lifecycle_by_recipient"][citizen]),
                     "job_chains": chains})
    return rows


def validate_communication(data, final, seed, arm, runtime_rows, decisions, assignments, completions):
    audit, messages, events, attempts = (data[key] for key in ("audit", "messages", "events", "attempts"))
    require(audit["world"] == final["world"] and audit["episode"] == final["episode"]
            and audit["capacity_denials"] == audit["recording_errors"] == audit["attempt_capacity_denials"] == 0
            and audit["history_quarantined"] == "false" and audit["strictly_read_only"] == "true"
            and audit["causal_benefit_established"] == "false", "Communication history lost, quarantined or mismatched")
    require(len(messages) == audit["messages"] == audit["delivered"]
            and len(events) == audit["events"] and len(attempts) == audit["send_attempts"] == audit["send_records"],
            "Incomplete communication export")
    by_message = {uuid(row["id"]): row for row in messages}
    require(len(by_message) == len(messages) and len({uuid(row["id"]) for row in attempts}) == len(attempts),
            "Duplicate message/send identity")
    require(len({(row["sender"], row["tick"]) for row in attempts}) == len(attempts)
            and len(attempts) == len(runtime_rows["SEND"]), "Duplicate or unaccounted bounded send opportunity")
    require([row["sequence"] for row in events] == list(range(1, len(events) + 1)),
            "Communication event sequence has gaps")
    actors = {actor_uuid(seed, slot) for slot in range(4)}
    for attempt in attempts:
        require(attempt["world"] == final["world"] and attempt["episode"] == final["episode"]
                and attempt["sender"] in actors and attempt["recipient"] in actors
                and attempt["sender"] != attempt["recipient"]
                and final["start_tick"] <= attempt["tick"] < final["end_tick"]
                and attempt["source"] in {source_key(source) for source in SOURCES}
                and attempt["outcome"] in ("DELIVERED", "DUPLICATE", "REJECTED")
                and isinstance(attempt["reason"], str) and bool(attempt["reason"]), "Invalid actual send attempt")
        matching = [row for row in runtime_rows["SEND"] if row["citizen"] == attempt["sender"]
                    and row["recipient"] == attempt["recipient"] and row["tick"] == attempt["tick"]
                    and source_key(row["source"]) == attempt["source"]]
        require(len(matching) == 1, "Send attempt has no matching runtime send")
        require(matching[0]["attempt_id"] == attempt["id"], "Runtime send changed native attempt identity")
        if arm == "NO_MESSAGES":
            require(attempt["outcome"] == "REJECTED" and attempt["reason"] == "NETWORK_DISABLED",
                    "Isolated arm transmitted information")
    require(sum(row["outcome"] == "REJECTED" for row in attempts) == audit["rejected_sends"]
            and sum(row["outcome"] == "DUPLICATE" for row in attempts) == audit["duplicate_sends"]
            and sum(row["outcome"] == "DELIVERED" for row in attempts) == len(messages),
            "Rejected or duplicate sends missing from totals")
    for message in messages:
        require(message["world"] == final["world"] and message["episode"] == final["episode"]
                and message["sender"] in actors and message["recipient"] in actors
                and message["sender"] != message["recipient"]
                and final["start_tick"] <= message["observed_tick"] <= message["sent_tick"] == message["delivered_tick"] < final["end_tick"]
                and message["sent_tick"] - message["observed_tick"] <= 40,
                "Message has foreign or stale direct-observation provenance")
        sends = [row for row in attempts if row["outcome"] == "DELIVERED"
                 and row.get("report_id") == message["report_id"] and row["recipient"] == message["recipient"]
                 and row["sender"] == message["sender"] and row["source"] == message["source"]
                 and row["tick"] == message["sent_tick"]]
        require(len(sends) == 1, "Message lacks exactly one successful actual send")
        send_row = next(row for row in runtime_rows["SEND"] if row["citizen"] == message["sender"]
                        and row["recipient"] == message["recipient"] and row["tick"] == message["sent_tick"])
        require(any(row["citizen"] == message["sender"] and source_key(row["source"]) == message["source"]
                    and row["tick"] == message["observed_tick"] and row["revision"] == message["source_revision"]
                    and row["wheat"] == message["reported_wheat"] and row["state"] in ("AVAILABLE", "EMPTY")
                    and row["sequence"] < send_row["sequence"] for row in runtime_rows["OBSERVE"]),
                "Message is not backed by sender's own prior direct observation")
    by_stage = {stage: [] for stage in ("DELIVERED", "READ", "SELECTED", "ASSIGNED", "PHYSICAL_COMPLETED")}
    for event in events:
        require(event["stage"] in by_stage and event["message_id"] in by_message, "Unknown communication event")
        message = by_message[event["message_id"]]
        require(event["actor"] == message["recipient"]
                and message["delivered_tick"] <= event["tick"] < final["end_tick"], "Event recipient/clock mismatch")
        by_stage[event["stage"]].append(event)
        if event["stage"] == "DELIVERED":
            require(event["tick"] == message["delivered_tick"] and "decision_id" not in event,
                    "Delivery falsely claimed policy use")
            continue
        require(event.get("decision_id") in decisions, "Communication use lacks actual policy decision")
        decision = decisions[event["decision_id"]]
        require(decision["citizen"] == event["actor"], "Communication used by wrong policy actor")
        if event["stage"] == "READ":
            require(event["tick"] == decision["tick"]
                    and 0 <= event["tick"] - message["observed_tick"] <= 200,
                    "Policy read outside common evidence-age rule")
            continue
        reads = [row for row in by_stage["READ"] if row["message_id"] == event["message_id"]
                 and row["decision_id"] == event["decision_id"] and row["sequence"] < event["sequence"]]
        require(len(reads) == 1 and decision.get("mode") == "REPORT_CUED_DIRECT_RECHECK"
                and decision.get("report_id") == message["report_id"]
                and decision["evidence_observed_tick"] == message["observed_tick"]
                and message["reported_wheat"] > 0
                and source_key(decision["source"]) == message["source"], "Selection used an unread or different report")
        if event["stage"] == "SELECTED":
            require(event["tick"] == decision["tick"], "Report selection clock mismatch")
            continue
        require(event.get("job_id") in assignments, "Communication assignment has no native job")
        assignment = assignments[event["job_id"]]
        require(assignment["decision"] == event["decision_id"] and assignment["citizen"] == event["actor"]
                and assignment["report_id"] == message["report_id"]
                and event["destination"] == source_key(DESTINATION), "Communication job binding mismatch")
        selected = [row for row in by_stage["SELECTED"] if row["message_id"] == event["message_id"]
                    and row["decision_id"] == event["decision_id"] and row["sequence"] < event["sequence"]]
        require(len(selected) == 1, "Job has no selected report")
        if event["stage"] == "ASSIGNED":
            require(event["tick"] == assignment["assigned_tick"], "Job assignment tick mismatch")
            continue
        require(event["job_id"] in completions
                and event["tick"] == completions[event["job_id"]]["delivered_tick"]
                and event["wheat_transferred"] == 1
                and event["witness"] == "EXECUTOR_INSERTION_RETURNED_NO_REMAINDER",
                "Communication completion lacks exact physical receipt")
        bound = [row for row in by_stage["ASSIGNED"] if row["job_id"] == event["job_id"]
                 and row["sequence"] < event["sequence"]]
        require(len(bound) == 1, "Physical completion has no unique accepted communication job")
    for stage, counter in (("DELIVERED", "delivered"), ("READ", "read"), ("SELECTED", "selected"),
                           ("ASSIGNED", "assigned"), ("PHYSICAL_COMPLETED", "physical_completed")):
        require(len(by_stage[stage]) == audit[counter], "Communication stage counter mismatch")
    for decision_id, decision in decisions.items():
        read = [row for row in by_stage["READ"] if row["decision_id"] == decision_id]
        require(len(read) == decision["report_inputs"]
                and len({row["message_id"] for row in read}) == len(read),
                "Actual policy reads differ from decision inputs")
        require(sum(row["decision_id"] == decision_id for row in by_stage["SELECTED"])
                == int(decision.get("mode") == "REPORT_CUED_DIRECT_RECHECK"),
                "Report-cued decision lost selection evidence or attached it to a direct decision")
    for job, assignment in assignments.items():
        expected = int(assignment["mode"] == "REPORT_CUED_DIRECT_RECHECK")
        require(sum(row["job_id"] == job for row in by_stage["ASSIGNED"]) == expected,
                "Assignment communication lifecycle missing or falsely attached")
        require(sum(row["job_id"] == job for row in by_stage["PHYSICAL_COMPLETED"]) == expected * int(job in completions),
                "Physical communication lifecycle missing or falsely attached")
    require(len({row["message_id"] for row in by_stage["DELIVERED"]}) == len(messages),
            "Message delivery duplicated or omitted")
    if arm == "NO_MESSAGES":
        require(not messages and not events and all(row.get("report_id") is None for row in assignments.values()),
                "Isolated arm consumed or acted on another citizen's information")
    if arm == "DIRECT_UNREAD":
        require(all(event["stage"] == "DELIVERED" for event in events)
                and all(row["report_inputs"] == 0 for row in decisions.values())
                and all(row.get("mode") != "REPORT_CUED_DIRECT_RECHECK" for row in decisions.values())
                and all(row.get("report_id") is None for row in assignments.values()),
                "Unread control exposed delivered reports to policy")
    used_messages = {row["message_id"] for row in by_stage["SELECTED"]}
    read_messages = {row["message_id"] for row in by_stage["READ"]}
    return {"send_attempts": len(attempts), "rejected_sends": audit["rejected_sends"],
            "duplicate_sends": audit["duplicate_sends"], "delivered_messages": len(messages),
            "policy_reads": len(by_stage["READ"]), "selected_reports": len(by_stage["SELECTED"]),
            "report_cued_assignments": len(by_stage["ASSIGNED"]),
            "report_cued_physical_jobs": len(by_stage["PHYSICAL_COMPLETED"]),
            "never_read_messages": len(messages) - len(read_messages),
            "never_selected_messages": len(messages) - len(used_messages),
            "expired_by_horizon": sum(row["expires_after_tick"] < final["end_tick"] for row in messages)}
