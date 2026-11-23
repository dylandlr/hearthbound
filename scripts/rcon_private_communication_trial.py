#!/usr/bin/env python3
"""Set up and observe one fixed-horizon private-worker Forge experiment.

After `start`, every RCON request is read-only until the horizon has ended.
Both arms can discover and haul without reports. Reports and runtime receipts
are joined to independent final inventories; a received message is not output.
"""
import contextlib
import json
import math
import re
import socket
import struct
import time
from uuid import UUID

from private_communication_protocol import (
    ARMS, CADENCE_TICKS, DESTINATION, DIMENSION, HORIZON_TICKS, INITIAL_STOCK,
    POSITIONS, RUNTIME_SCHEMA, SOURCES, WALL_GUARD_SECONDS, actor_uuid,
    matched_manifest,
)
from rcon_two_citizen_haul_acceptance import exact, packet

MARKER = "COMMUNICATION_TRIAL_V1 "
COMMAND = "hearthbound-communication-trial"
SETUP_COMMANDS = (
    "gamerule doMobSpawning false", "gamerule doDaylightCycle false",
    "gamerule doWeatherCycle false", "gamerule randomTickSpeed 0",
    "time set 6000", "weather clear", "forceload add -16 -16 47 47",
    "fill -16 100 -16 40 105 32 minecraft:air",
    "fill 0 100 0 24 100 16 minecraft:stone",
    "fill 0 101 0 0 104 16 minecraft:stone",
    "fill 24 101 0 24 104 16 minecraft:stone",
    "fill 0 101 0 24 104 0 minecraft:stone",
    "fill 0 101 16 24 104 16 minecraft:stone",
    "fill 0 104 0 24 104 16 minecraft:stone",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def uuid(value):
    require(isinstance(value, str) and str(UUID(value)) == value, "Noncanonical UUID")
    return value


def uuid_ints(value):
    raw = UUID(value).bytes
    return list(struct.unpack(">iiii", raw))


def xyz(position):
    return " ".join(str(value) for value in position)


def source_key(position):
    return DIMENSION + "|" + ",".join(str(value) for value in position)


def packed(position):
    x, y, z = position
    value = ((x & 0x3ffffff) << 38) | ((z & 0x3ffffff) << 12) | (y & 0xfff)
    return value if value < 2**63 else value - 2**64


def read_frame(sock):
    length = struct.unpack("<i", exact(sock, 4))[0]
    require(10 <= length <= 1_000_000, "Invalid RCON frame size")
    frame = exact(sock, length)
    require(frame[-2:] == b"\0\0", "Invalid RCON terminator")
    request_id, kind = struct.unpack("<ii", frame[:8])
    return request_id, kind, frame[8:-2].decode("utf-8", errors="strict")


class MultipartRcon:
    """Read all fragments before a queued read-only `list` delimiter.

    Minecraft may split a single response into 4096-byte packets. A separate
    request ID, processed after the requested command, removes dependence on
    packet size or timing and avoids losing later pages to response mismatch.
    """
    def __init__(self, sock):
        self.sock = sock
        self.next_id = 10

    def run(self, command):
        request_id, delimiter_id = self.next_id, self.next_id + 1
        self.next_id += 2
        # Vanilla's reader may consume only one incoming request per TCP read.
        # Wait for the first command response before transmitting the delimiter.
        # See MCDReforged's client rationale:
        # https://docs.mcdreforged.com/en/latest/_modules/mcdreforged/minecraft/rcon/rcon_connection.html
        self.sock.sendall(packet(request_id, 2, command))
        actual, kind, first = read_frame(self.sock)
        require(actual == request_id and kind == 0, "Invalid first RCON response identity/kind")
        self.sock.sendall(packet(delimiter_id, 2, "list"))
        parts, size = [first], len(first.encode())
        for _ in range(511):
            actual, kind, payload = read_frame(self.sock)
            require(kind == 0, "Unexpected RCON response kind")
            if actual == delimiter_id:
                require(bool(parts), "RCON delimiter arrived before command response")
                result = "".join(parts)
                require(bool(result.strip()), "Empty RCON command response")
                print("PRIVATE_COMMUNICATION_RCON command=" + repr(command)
                      + " response=" + repr(result), flush=True)
                return result
            require(actual == request_id, "Out-of-order RCON response identity")
            size += len(payload.encode())
            require(size <= 2 * 1024 * 1024, "Oversized multipart RCON response")
            parts.append(payload)
        raise ValueError("Too many RCON fragments")

    def require(self, command, expected):
        response = self.run(command)
        require(expected.lower() in response.lower(),
                f"Expected {expected!r}: {command}: {response}")
        return response

    def stop_server(self):
        """Terminal command: never queue a delimiter behind server shutdown.

        The server thread joins its RCON thread while stopping. A queued `list`
        can leave that thread waiting for the stopped server to execute it.
        The caller closes this connection immediately after the first reply.
        """
        request_id = self.next_id
        self.next_id += 1
        self.sock.sendall(packet(request_id, 2, "stop"))
        actual, kind, response = read_frame(self.sock)
        require(actual == request_id and kind == 0, "Invalid terminal RCON response")
        require("Stopping the server" in response, "Unexpected terminal RCON acknowledgement")
        print("PRIVATE_COMMUNICATION_RCON command='stop' response=" + repr(response), flush=True)
        return response


@contextlib.contextmanager
def connection(password):
    with socket.create_connection(("127.0.0.1", 25575), timeout=20) as sock:
        sock.settimeout(20)
        sock.sendall(packet(1, 3, password))
        for _ in range(4):
            request_id, kind, _ = read_frame(sock)
            require(request_id != -1, "RCON authentication rejected")
            if request_id == 1 and kind == 2:
                yield MultipartRcon(sock)
                return
        raise ValueError("RCON authentication response missing")


def runtime(rcon, suffix="audit"):
    response = rcon.require(f"{COMMAND} {suffix}", MARKER)
    parsed = json.loads(response.split(MARKER, 1)[1])
    require(parsed["schema"] == RUNTIME_SCHEMA, "Unexpected runtime schema")
    return parsed


def pages(rcon, kind, scope=None):
    result, total = [], None
    expected_scope = ({key: scope[key] for key in ("world", "episode", "dimension")}
                      if scope is not None else None)
    while total is None or len(result) < total:
        require(len(result) <= 4096, "Unbounded runtime export")
        page = runtime(rcon, f"{kind} {len(result)}")
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


def communication_audit(rcon):
    response = rcon.require("hearthbound-communication audit", "CITIZEN_COMMUNICATION_AUDIT_V1 ")
    values = dict(re.findall(r"\b([a-z_]+)=([^\s]+)", response))
    for key in ("send_attempts", "rejected_sends", "duplicate_sends", "messages", "events",
                "delivered", "read", "selected", "assigned", "physical_completed",
                "capacity_denials", "recording_errors", "send_records", "attempt_capacity_denials"):
        values[key] = int(values[key])
    return values


def communication_pages(rcon, kind, scope):
    result, total = [], None
    marker = f"CITIZEN_COMMUNICATION_{kind.upper()}_V1 "
    while total is None or len(result) < total:
        require(len(result) <= 8192, "Unbounded communication export")
        response = rcon.require(f"hearthbound-communication {kind} {len(result)}", marker)
        page = json.loads(response.split(marker, 1)[1])
        require(page["kind"] == kind and page["offset"] == len(result),
                "Communication pagination identity mismatch")
        require(page["world"] == scope["world"] and page["dimension"] == DIMENSION,
                "Communication page changed world/dimension")
        require(page["strictly_read_only"] is True
                and page["inventory_delta_verified"] is False
                and page["causal_benefit_established"] is False,
                "Communication export improperly asserts causal or physical credit")
        if total is not None:
            require(page["total"] == total, "Communication history changed during export")
        total = page["total"]
        require(type(total) is int and 0 <= total <= 8192, "Invalid communication record total")
        rows = page["records"]
        require(isinstance(rows, list), "Invalid communication records")
        if not rows:
            require(len(result) == total, "Truncated communication export")
            break
        result.extend(rows)
        require(len(result) <= total, "Communication export exceeded total")
    return result


def communication_snapshot(rcon):
    before = communication_audit(rcon)
    result = {"audit": before}
    for kind in ("messages", "events", "attempts"):
        result[kind] = communication_pages(rcon, kind, before)
    require(communication_audit(rcon) == before, "Communication changed during frozen export")
    return result


def inventory(rcon, position):
    response = rcon.require(f"data get block {xyz(position)} Items", "block data:")
    payload = response.split("block data:", 1)[1].strip()
    if payload == "[]":
        return {"wheat": 0, "raw": response}
    require(payload.startswith("[") and payload.endswith("]"), "Invalid inventory response")
    entries = re.findall(r"\{([^{}]*)\}", payload)
    require(len(entries) == 1, "Unexpected chest contents or multiple stacks")
    require(re.search(r'\bid:\s*"minecraft:wheat"', entries[0]) is not None,
            "Unexpected item type in fixture chest")
    counts = re.findall(r"\bCount:\s*(\d+)b\b", entries[0])
    require(len(counts) == 1 and 1 <= int(counts[0]) <= sum(INITIAL_STOCK),
            "Unexpected wheat count")
    return {"wheat": int(counts[0]), "raw": response}


def inventories(rcon):
    return {"sources": [inventory(rcon, position) for position in SOURCES],
            "destination": inventory(rcon, DESTINATION)}


def actor_witness(rcon, citizen):
    uuid(citizen)
    no_ai = rcon.require(f"data get entity {citizen} NoAI", "entity data:")
    require(re.search(r":\s*1b\s*$", no_ai) is not None, "Actor is not frozen")
    position = rcon.require(f"data get entity {citizen} Pos", "entity data:")
    payload = position.split("entity data:", 1)[1].strip()
    coordinates = [float(value) for value in re.findall(r"(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)d", payload)]
    require(len(coordinates) == 3 and all(math.isfinite(value) for value in coordinates),
            "Invalid native actor position")
    rotation_raw = rcon.require(f"data get entity {citizen} Rotation", "entity data:")
    rotation_payload = rotation_raw.split("entity data:", 1)[1].strip()
    rotation = [float(value) for value in re.findall(r"(-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?)f", rotation_payload)]
    require(len(rotation) == 2 and all(math.isfinite(value) for value in rotation), "Invalid native actor rotation")
    cargo_path = 'ForgeData."hearthbound.haul".cargo'
    cargo_present = rcon.run(f"execute if data entity {citizen} {cargo_path}")
    cargo_wheat, cargo_raw = 0, None
    if "Test passed" in cargo_present:
        cargo_raw = rcon.require(f"data get entity {citizen} {cargo_path}", "entity data:")
        require('"minecraft:wheat"' in cargo_raw, "Unexpected carried item")
        matches = re.findall(r"\bCount:\s*(\d+)b\b", cargo_raw)
        require(len(matches) == 1 and int(matches[0]) == 1, "Invalid physical cargo count")
        cargo_wheat = 1
    else:
        require("Test failed" in cargo_present, "Unknown cargo existence response")
    haul = rcon.run(f'data get entity {citizen} ForgeData."hearthbound.haul"')
    motor = None
    if "entity data:" in haul:
        motor = {}
        for key in ("phase", "source", "destination", "assignedTick", "physicalDeliveredTick"):
            matches = re.findall(r"\b" + key + r":\s*(-?\d+)(?:L)?\b", haul)
            require(len(matches) <= 1, "Ambiguous native haul field")
            if matches:
                motor[key] = int(matches[0])
        match = re.search(r"\bjobId:\s*\[I;\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\]", haul)
        require(match is not None, "Native haul has no actual job identity")
        motor["job"] = str(UUID(bytes=struct.pack(">iiii", *map(int, match.groups()))))
    else:
        require("Found no elements matching" in haul, "Unknown native haul response")
    return {"citizen": citizen, "no_ai": True, "position": coordinates,
            "cargo_wheat": cargo_wheat, "cargo_raw": cargo_raw, "haul_raw": haul,
            "no_ai_raw": no_ai, "position_raw": position, "rotation": rotation,
            "rotation_raw": rotation_raw, "motor": motor}


def validate_setup_response(command, response):
    if command.startswith("gamerule "):
        require("is now set to:" in response, "Failed gamerule setup: " + response)
    elif command.startswith("time "):
        require("Set the time to 6000" in response, "Failed clock setup: " + response)
    elif command.startswith("weather "):
        require(response.strip() == "Set the weather to clear", "Failed weather setup: " + response)
    elif command.startswith("forceload "):
        require("force loaded" in response, "Failed chunk setup: " + response)
    else:
        require("Successfully filled" in response or (command.endswith("minecraft:air")
                and "No blocks were filled" in response), "Failed arena construction: " + response)


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
    data["configured"] = runtime(rcon, f"configure {arm} {seed} {HORIZON_TICKS} {xyz(DESTINATION)}")
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
    data["claims_after_raw"] = rcon.require("hearthboundclaims count", "Active source claims")
    match = re.search(r"Active source claims in this dimension: (\d+)", data["claims_after_raw"])
    require(match is not None, "Missing source claim count")
    data["claims_after"] = int(match[1])
    data["final_after_export"] = runtime(rcon)
    data["inventories_after_export"] = inventories(rcon)
    require(data["inventories_after_export"] == data["inventories_after"],
            "Physical inventories changed after fixed horizon")
    data["metrics"] = validate_trial(data, seed, arm)
    print("PRIVATE_COMMUNICATION_PHYSICAL_PASS " + json.dumps(data["metrics"], sort_keys=True), flush=True)
    return data


def validate_trial(data, seed, arm):
    """Validate the fixed horizon, budget, provenance, and physical conservation."""
    return validate_runtime_evidence(data, seed, arm)


def validate_initial(data, seed, arm):
    manifest = matched_manifest(seed)
    require(data["declared_initial_manifest"] == manifest, "Initial contract mismatch")
    require([row["command"] for row in data["setup_commands"]] == list(SETUP_COMMANDS), "Arena setup contract changed")
    for row in data["setup_commands"]:
        validate_setup_response(row["command"], row["response"])
    configured = data["configured"]
    require(configured["schema"] == RUNTIME_SCHEMA and configured["status"] == "CONFIGURED"
            and configured["arm"] == arm and configured["policy_seed"] == seed
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
    final = data["final"]
    require(data["declared_initial_manifest"] == matched_manifest(seed), "Initial contract mismatch")
    require(final["schema"] == RUNTIME_SCHEMA and final["status"] == "COMPLETE"
            and final["arm"] == arm and final["policy_seed"] == seed
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
    by_kind = {kind: [] for kind in ("OBSERVE", "SEND", "DECISION", "ASSIGNED", "COMPLETE")}
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
                and actor["no_ai"] is True and actor["present"] is True
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
    delivery_ticks = sorted(row["delivered_tick"] - final["start_tick"] for row in completions.values())
    return {"physical_wheat_delivered": delivered, "source_wheat_remaining": sum(row["wheat"] for row in after["sources"]),
            "cargo_wheat_at_horizon": cargo, "unfinished_jobs": len(inflight), "inflight": inflight,
            "first_delivery_relative_tick": delivery_ticks[0] if delivery_ticks else None,
            "all_four_delivery_relative_tick": delivery_ticks[-1] if delivered == sum(INITIAL_STOCK) else None,
            "all_four_censored_at_tick": None if delivered == sum(INITIAL_STOCK) else HORIZON_TICKS,
            "output_ticks": sum(HORIZON_TICKS - tick for tick in delivery_ticks),
            "game_ticks": HORIZON_TICKS, "horizon_wall_seconds": data["horizon_wall_seconds"],
            "actor_contributions": contributions, "costs": totals, "communication": comm,
            "direct_only_physical_jobs": sum(assignments[job]["mode"] == "DIRECT_MEMORY_RECHECK" for job in completions),
            "communication_win_required": False, "causal_benefit_established": False}


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
                and attempt["outcome"] in ("DELIVERED", "DUPLICATE", "REJECTED"), "Invalid actual send attempt")
        matching = [row for row in runtime_rows["SEND"] if row["citizen"] == attempt["sender"]
                    and row["recipient"] == attempt["recipient"] and row["tick"] == attempt["tick"]
                    and source_key(row["source"]) == attempt["source"]]
        require(len(matching) == 1, "Send attempt has no matching runtime send")
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
