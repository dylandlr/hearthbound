#!/usr/bin/env python3
"""Post-window observations that never repair or rescore a colony trial."""
import copy
import hashlib
import json
from pathlib import Path
import re
import time
from uuid import UUID

from haul_motor_diagnostics import canonical_uuid, command_for, parse_snapshot

SCHEMA = "hearthbound.colony-post-window-motor-diagnostics.v1"
FILENAME = "motor-diagnostics.json"
ROUNDS = 3
INTERVAL_SECONDS = 1.0
EXPECTED_CITIZENS = 4
SOURCES = (4, 12, 20, 28)
READINESS = "COLONY_SOURCE_READINESS_V0_9"
PHASE = "AFTER_FIXTURE_AND_TERMINAL_SCORE"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def roster_response(response, expected_source=None):
    if not isinstance(response, str) or not response.strip().startswith(READINESS + " "):
        raise ValueError("Missing source-readiness roster")
    tokens = response.strip().split()
    values = {}
    for token in tokens[1:]:
        key, separator, value = token.partition("=")
        if not separator or key in values:
            raise ValueError("Malformed or duplicate roster field")
        values[key] = value
    for key, expected in (("strictly_read_only", "true"), ("policy_control", "false"),
                          ("reward_authorized", "false"), ("source_chunk_loaded", "true"),
                          ("truncated", "false")):
        if values.get(key) != expected:
            raise ValueError("Incomplete or changed roster contract: " + key)
    if "unknown_unloaded" in values:
        raise ValueError("Unloaded roster cannot be treated as complete")
    if expected_source is not None and values.get("source") != ",".join(map(str, expected_source)):
        raise ValueError("Roster describes another source")
    if not re.fullmatch(r"\d+", values.get("citizens", "")):
        raise ValueError("Missing roster citizen count")
    rows = re.findall(r"\bcitizen_(\d+)=([0-9a-f-]+),pos:", response)
    if len(rows) != int(values["citizens"]) or [int(i) for i, _ in rows] != list(range(len(rows))):
        raise ValueError("Roster count or indices disagree")
    citizens = [canonical_uuid(citizen) for _, citizen in rows]
    if len(set(citizens)) != len(citizens):
        raise ValueError("Repeated citizen in roster response")
    return citizens


def native_commands(citizen, field):
    canonical_uuid(citizen)
    if field not in ("jobId", "phase", "cargo"):
        raise ValueError("Unsupported native haul field")
    path = f'ForgeData."hearthbound.haul".{field}'
    return (f"execute if data entity {citizen} {path}",
            f"data get entity {citizen} {path}")


def native_witness(rcon, citizen, field):
    presence_command, data_command = native_commands(citizen, field)
    presence = rcon.run(presence_command)
    result = {"presence_command": presence_command, "presence_response": presence,
              "data_command": None, "data_response": None}
    if presence.strip() == "Test passed, count: 1":
        result["data_command"] = data_command
        result["data_response"] = rcon.run(data_command)
    elif presence.strip() != "Test failed":
        raise ValueError("Native haul presence probe was unavailable or malformed")
    validate_native_witness(result, citizen, field)
    return result


def validate_native_witness(witness, citizen, field):
    """Recognize native values and their exact UUID commands, not Sable's name.

    These are later non-atomic reads. A different value from the preceding
    snapshot may reflect actual ongoing execution and never changes the score.
    """
    presence_command, data_command = native_commands(citizen, field)
    if not isinstance(witness, dict) or witness.get("presence_command") != presence_command:
        raise ValueError("Native witness targets another citizen or field")
    presence = witness.get("presence_response")
    if not isinstance(presence, str) or len(presence.encode()) > 3900:
        raise ValueError("Unbounded or missing native presence response")
    if presence.strip() == "Test failed":
        if witness.get("data_command") is not None or witness.get("data_response") is not None:
            raise ValueError("Absent native field has invented data")
        return {"status": "ABSENT_AT_NATIVE_PROBE", "value": None}
    if presence.strip() != "Test passed, count: 1" or witness.get("data_command") != data_command:
        raise ValueError("Native presence or subject binding is invalid")
    response = witness.get("data_response")
    if not isinstance(response, str) or len(response.encode()) > 3900:
        raise ValueError("Unbounded or missing native value response")
    match = re.fullmatch(r"[^\n]+ has the following entity data: (.+)", response.strip())
    if not match:
        raise ValueError("Native data query failed or returned an unrecognized response")
    value = match[1]
    if field == "jobId":
        parts = re.fullmatch(r"\[I;\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\]", value)
        if not parts or any(not -(2 ** 31) <= int(number) < 2 ** 31 for number in parts.groups()):
            raise ValueError("Native job UUID is not a four-int NBT array")
        number = 0
        for part in parts.groups():
            number = (number << 32) | (int(part) & 0xffffffff)
        value = str(UUID(int=number))
    elif field == "phase":
        if not re.fullmatch(r"-?\d+", value) or not -(2 ** 31) <= int(value) < 2 ** 31:
            raise ValueError("Native phase is not an integer NBT value")
        value = int(value)
    else:
        item = re.findall(r'id:\s*"([a-z0-9_.-]+:[a-z0-9_./-]+)"', value)
        count = re.findall(r"Count:\s*(-?\d+)b", value)
        remaining = re.sub(r'id:\s*"[a-z0-9_.-]+:[a-z0-9_./-]+"|Count:\s*-?\d+b', "", value)
        if (len(item) != 1 or len(count) != 1 or not value.startswith("{") or not value.endswith("}")
                or re.sub(r"[\s{},]", "", remaining) or not -128 <= int(count[0]) <= 127):
            raise ValueError("Native cargo is not the fixture's plain item-stack compound")
        value = {"item": item[0], "count": int(count[0])}
    return {"status": "OBSERVED_NATIVE_VALUE", "value": value}


def sequence_findings(report):
    """Describe measured sequences; never infer a motor root cause or reward."""
    findings = []
    for citizen in report["citizens"]:
        samples = [row["snapshot"] for group in report["rounds"] for row in group["citizens"]
                   if row["citizen"] == citizen and row.get("snapshot", {}).get("status") == "OBSERVED"]
        flags = []
        game_delta = entity_delta = None
        if samples:
            last = samples[-1]
            entity, motor, haul = last["entity"], last["motor"], last["haul"]
            if motor["active"] and not entity["position_entity_ticking"]:
                flags.append("ACTIVE_JOB_OUTSIDE_ENTITY_TICKING_AT_LAST_SAMPLE")
            if motor["active"] and entity["no_ai"]:
                flags.append("ACTIVE_JOB_WITH_NO_AI_AT_LAST_SAMPLE")
            if motor["active"] and not entity["can_update"]:
                flags.append("ACTIVE_JOB_WITH_UPDATES_DISABLED_AT_LAST_SAMPLE")
            if motor["paused"]:
                flags.append("PAUSED_AT_LAST_SAMPLE")
            if motor["quarantined"]:
                flags.append("QUARANTINED_AT_LAST_SAMPLE")
            if motor["active"] and haul["cargo"]["present"]:
                flags.append("ACTIVE_JOB_HAS_CARGO_TAG_AT_LAST_SAMPLE")
            if motor["active"] and last["claim"]["owned_by_citizen"] is False:
                flags.append("ACTIVE_JOB_WITHOUT_MATCHING_SOURCE_OWNER_AT_LAST_SAMPLE")
            if motor["active"] and last["claim"]["owned_by_citizen"] is None:
                flags.append("ACTIVE_JOB_SOURCE_OWNER_UNAVAILABLE_AT_LAST_SAMPLE")
            if (motor["active"] and motor["within_reach"] is False
                    and last["navigation"]["done"]):
                flags.append("NAVIGATION_DONE_OUTSIDE_MOTOR_REACH_AT_LAST_SAMPLE")
        if len(samples) >= 2:
            first, last = samples[0], samples[-1]
            game_delta = last["tick"] - first["tick"]
            entity_delta = last["entity"]["tick_count"] - first["entity"]["tick_count"]
            advancing_world = all(b["tick"] > a["tick"] for a, b in zip(samples, samples[1:]))
            stable_entity_ticks = len({row["entity"]["tick_count"] for row in samples}) == 1
            if advancing_world and stable_entity_ticks:
                flags.append("ENTITY_TICK_COUNT_UNCHANGED_WHILE_WORLD_ADVANCED")
                if all(not row["entity"]["position_entity_ticking"] for row in samples):
                    flags.append("LOADED_NON_TICKING_SEQUENCE_OBSERVED")
            jobs = [row["haul"]["job"] for row in samples]
            if (jobs[0] is not None and len(set(jobs)) == 1 and first["haul"]["phase"] != 2
                    and last["haul"]["phase"] == 2):
                flags.append("JOB_COMPLETED_DURING_POST_WINDOW_SAMPLING")
        findings.append({"citizen": citizen, "observed_samples": len(samples),
                         "game_tick_delta": game_delta, "entity_tick_delta": entity_delta,
                         "flags": flags, "root_cause_established": False})
    return findings


def capture(rcon, terminal_snapshot, sleep=time.sleep):
    report = {"schema": SCHEMA, "phase": PHASE, "strictly_read_only": True,
              "score_recomputed": False, "collection_atomic": False,
              "terminal_snapshot_sha256": digest(terminal_snapshot),
              "terminal_snapshot_before_sampling": copy.deepcopy(terminal_snapshot),
              "expected_citizens": EXPECTED_CITIZENS, "planned_rounds": ROUNDS,
              "interval_wall_seconds": INTERVAL_SECONDS,
              "roster_scope": "UNION_OF_LOADED_MARKED_CITIZENS_WITHIN_16_OF_FOUR_FIXTURE_SOURCES",
              "roster_queries": [], "citizens": [], "rounds": [], "errors": [],
              "status": "INCOMPLETE", "findings": []}
    known = set()
    try:
        for x in SOURCES:
            command = f"hearthbound-colony source-readiness-audit {x} 100 1"
            raw = rcon.run(command)
            row = {"source": [x, 100, 1], "command": command, "response": raw}
            report["roster_queries"].append(row)
            row["citizens"] = roster_response(raw, [x, 100, 1])
            known.update(row["citizens"])
        report["citizens"] = sorted(known)
        if len(known) != EXPECTED_CITIZENS:
            raise ValueError("Post-window roster does not contain exactly four known citizens")
        for index in range(ROUNDS):
            if index:
                sleep(INTERVAL_SECONDS)
            group = {"index": index, "citizens": []}
            report["rounds"].append(group)
            for citizen in report["citizens"]:
                raw = rcon.run(command_for(citizen))
                row = {"citizen": citizen, "response": raw}
                group["citizens"].append(row)
                row["snapshot"] = parse_snapshot(raw, citizen, expected_dimension="minecraft:overworld")
                if index in (0, ROUNDS - 1):
                    # Independent native NBT witnesses, each bounded by the fixture's
                    # plain one-wheat cargo and UUID/phase scalar. They are separate
                    # server commands and may observe legitimate later transitions.
                    row["native_haul_witnesses"] = {
                        field: native_witness(rcon, citizen, field) for field in ("jobId", "phase", "cargo")}
        observed = [row["snapshot"] for group in report["rounds"] for row in group["citizens"]]
        if any(row["status"] != "OBSERVED" for row in observed):
            raise ValueError("A declared citizen was not observable in every post-window round")
        if len({row["world"] for row in observed}) != 1 or any(row["world_state"] != "PRESENT" for row in observed):
            raise ValueError("Post-window snapshots lack a common existing world identity")
        report["status"] = "COMPLETE"
    except Exception as error:
        report["citizens"] = sorted(known)
        report["errors"].append(type(error).__name__ + ": " + str(error))
    try:
        report["findings"] = sequence_findings(report)
    except (ValueError, KeyError, TypeError) as error:
        report["status"] = "INCOMPLETE"
        report["errors"].append("Sequence analysis: " + type(error).__name__ + ": " + str(error))
    return report


def validate_report(report, record):
    """Validate the separate diagnostic evidence without changing trial scoring."""
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        raise ValueError("Wrong post-window diagnostic schema")
    expected = {"phase": PHASE, "strictly_read_only": True, "score_recomputed": False,
                "collection_atomic": False, "expected_citizens": EXPECTED_CITIZENS,
                "planned_rounds": ROUNDS, "interval_wall_seconds": INTERVAL_SECONDS}
    for key, value in expected.items():
        if type(report.get(key)) is not type(value) or report[key] != value:
            raise ValueError("Changed post-window contract: " + key)
    if (report.get("terminal_snapshot_sha256") != digest(record.get("terminal_snapshot"))
            or report.get("terminal_snapshot_before_sampling") != record.get("terminal_snapshot")):
        raise ValueError("Diagnostics are not bound to the original terminal score")
    if report.get("status") != "COMPLETE" or report.get("errors"):
        raise ValueError("Post-window diagnostic capture was incomplete")
    citizens = report.get("citizens")
    if (not isinstance(citizens, list) or len(citizens) != EXPECTED_CITIZENS
            or citizens != sorted(set(citizens))):
        raise ValueError("Diagnostic citizen denominator changed")
    for citizen in citizens:
        canonical_uuid(citizen)
    queries = report.get("roster_queries")
    if not isinstance(queries, list) or len(queries) != len(SOURCES):
        raise ValueError("Missing roster observations")
    reconstructed = set()
    for x, row in zip(SOURCES, queries):
        if row["source"] != [x, 100, 1] or row["command"] != f"hearthbound-colony source-readiness-audit {x} 100 1":
            raise ValueError("Unexpected roster source")
        values = roster_response(row["response"], [x, 100, 1])
        if values != row["citizens"]:
            raise ValueError("Roster disagrees with raw response")
        reconstructed.update(values)
    if sorted(reconstructed) != citizens:
        raise ValueError("Citizen roster was replaced")
    rounds = report.get("rounds")
    if not isinstance(rounds, list) or len(rounds) != ROUNDS:
        raise ValueError("Missing post-window rounds")
    prior_ticks = {}
    native_coverage = {"OBSERVED_NATIVE_VALUE": 0, "ABSENT_AT_NATIVE_PROBE": 0}
    world = record.get("world", {}).get("world_uuid")
    canonical_uuid(world)
    for index, group in enumerate(rounds):
        if group.get("index") != index or [row["citizen"] for row in group["citizens"]] != citizens:
            raise ValueError("Round order or citizen coverage changed")
        for row in group["citizens"]:
            snapshot = parse_snapshot(row["response"], row["citizen"], world, "minecraft:overworld")
            if snapshot != row["snapshot"] or snapshot["status"] != "OBSERVED":
                raise ValueError("Snapshot differs from its actual command response")
            if snapshot["tick"] < prior_ticks.get(row["citizen"], -1):
                raise ValueError("Post-window server time moved backwards")
            prior_ticks[row["citizen"]] = snapshot["tick"]
            if index in (0, ROUNDS - 1):
                witnesses = row.get("native_haul_witnesses")
                if not isinstance(witnesses, dict) or set(witnesses) != {"jobId", "phase", "cargo"}:
                    raise ValueError("Missing independent native haul witnesses")
                for field, witness in witnesses.items():
                    checked = validate_native_witness(witness, row["citizen"], field)
                    native_coverage[checked["status"]] += 1
    findings = sequence_findings(report)
    if findings != report.get("findings"):
        raise ValueError("Sequence findings differ from their observations")
    return {"status": "VERIFIED_COMPLETE", "citizens": len(citizens), "snapshots": ROUNDS * len(citizens),
            "phase": PHASE, "score_recomputed": False, "findings": findings,
            "native_field_read_coverage": native_coverage,
            "native_witnesses_are_separate_nonatomic_reads": True}


def inspect_artifact(directory, record, required=False):
    """Keep diagnostic corruption separate from the original accounting estimate."""
    if not required and record.get("motor_diagnostics_required") is not True:
        return {"status": "NOT_REQUIRED_FOR_THIS_REVISION", "findings": []}
    metadata = record.get("motor_diagnostics")
    if not isinstance(metadata, dict) or not metadata.get("file"):
        return {"status": "UNAVAILABLE", "findings": [], "error": (metadata or {}).get("error")
                if isinstance(metadata, dict) else "No completed diagnostic capture"}
    try:
        if metadata.get("file") != FILENAME:
            raise ValueError("Unexpected diagnostic artifact path")
        path = Path(directory) / FILENAME
        if path.is_symlink():
            raise ValueError("Diagnostic artifact is a symbolic link")
        payload = path.read_bytes()
        if len(payload) > 512 * 1024 or hashlib.sha256(payload).hexdigest() != metadata.get("sha256"):
            raise ValueError("Diagnostic artifact size or digest mismatch")
        report = json.loads(payload)
        if metadata.get("status") != "COMPLETE":
            return {"status": "CAPTURE_INCOMPLETE", "artifact_digest_verified": True,
                    "findings": [], "capture_status": metadata.get("status"),
                    "error": metadata.get("error")}
        return validate_report(report, record)
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError) as error:
        return {"status": "INVALID_DIAGNOSTIC_EVIDENCE", "findings": [],
                "error": type(error).__name__ + ": " + str(error)}
