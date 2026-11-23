#!/usr/bin/env python3
"""Post-window observations that never repair or rescore a colony trial."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import time
from uuid import UUID

from haul_motor_diagnostics import canonical_uuid, command_for, parse_snapshot

SCHEMA = "hearthbound.colony-post-window-motor-diagnostics.v2"
FILENAME = "motor-diagnostics.json"
ROUNDS = 3
INTERVAL_SECONDS = 1.0
EXPECTED_CITIZENS = 4
SOURCES = (4, 12, 20, 28)
READINESS = "COLONY_SOURCE_READINESS_V0_9"
PHASE = "AFTER_FIXTURE_AND_TERMINAL_SCORE"
TRACE_COMMAND = "hearthbound-colony decision-traces"
TRACE_PREFIX = "COLONY_TRACES_V0_4"
TRACE_SCOPE = "LOADED_LATEST_CITIZEN_MEMORY_AND_PHYSICAL_JOB"
TRACE_SOURCE = "ORIGINAL_FIXTURE_RCON_RESPONSE_BEFORE_TERMINAL_SCORE"
TRACE_IDENTITY = "RETAINED_FIXTURE_DECISION_TRACES"
FALLBACK_IDENTITY = "CURRENT_SOURCE_ROSTER_FALLBACK"
ROSTER_SCOPE = "LOADED_MARKED_CITIZENS_WITHIN_16_OF_FOUR_FIXTURE_SOURCES"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def trace_response(response):
    """Validate the original fixture's complete physical-decision trace envelope."""
    if (not isinstance(response, str) or len(response.encode()) > 3900
            or not response.strip().startswith(TRACE_PREFIX + " ")):
        raise ValueError("Missing or unbounded retained decision trace")
    values = {}
    for token in response.strip().split()[1:]:
        key, separator, value = token.partition("=")
        if not separator or key in values:
            raise ValueError("Malformed or duplicate decision trace field")
        values[key] = value
    if set(values) != {"count", "episode", "scope", "entries", "learning_authorized", "reward_authorized"}:
        raise ValueError("Changed decision trace envelope")
    if (values["count"] != str(EXPECTED_CITIZENS) or values["scope"] != TRACE_SCOPE
            or values["learning_authorized"] != "false" or values["reward_authorized"] != "false"):
        raise ValueError("Incomplete or unauthorized decision trace")
    episode = canonical_uuid(values["episode"])
    entries = []
    for encoded in values["entries"].split(";"):
        fields = encoded.split(",")
        if len(fields) != 10:
            raise ValueError("Decision trace entry has the wrong field count")
        task, citizen, job, decision, evidence, revision, observed, decided, assigned, delivered = fields
        identifiers = [canonical_uuid(value) for value in (citizen, job, decision, evidence)]
        numeric = (task, revision, observed, decided, assigned, delivered)
        if any(not re.fullmatch(r"0|[1-9][0-9]{0,18}", value) for value in numeric):
            raise ValueError("Decision trace contains a non-canonical integer")
        task_id, revision_id, t0, t1, t2, t3 = map(int, numeric)
        if (any(value > 2 ** 63 - 1 for value in (task_id, revision_id, t0, t1, t2, t3))
                or not (task_id > 0 and revision_id > 0 and 0 <= t0 <= t1 <= t2 <= t3
                        and t2 - t0 <= 20)):
            raise ValueError("Invalid decision trace chronology")
        entries.append(dict(zip(("task_id", "citizen", "job", "decision", "evidence", "revision",
                                 "observed_tick", "decision_tick", "assigned_tick", "delivered_tick"),
                                (task_id, *identifiers, revision_id, t0, t1, t2, t3))))
    if (len(entries) != EXPECTED_CITIZENS or any(len({entry[key] for entry in entries}) != EXPECTED_CITIZENS
            for key in ("task_id", "citizen", "job", "decision", "evidence"))):
        raise ValueError("Decision trace does not identify four distinct citizens and jobs")
    return {"count": EXPECTED_CITIZENS, "episode": episode, "scope": TRACE_SCOPE,
            "entries": entries, "learning_authorized": False, "reward_authorized": False}


def retained_trace(queries):
    """Reconstruct roster authority from retained bytes, never a fresh command."""
    if not isinstance(queries, list) or len(queries) != 1:
        raise ValueError("Expected exactly one retained fixture decision trace")
    row = queries[0]
    if (not isinstance(row, dict) or row.get("source") != TRACE_SOURCE
            or row.get("command") != TRACE_COMMAND
            or type(row.get("request_id")) is not int or not 20 <= row["request_id"] < 2 ** 31):
        raise ValueError("Retained trace has invalid command provenance")
    response = row.get("response")
    parsed = trace_response(response)
    if row.get("response_sha256") != hashlib.sha256(response.encode()).hexdigest():
        raise ValueError("Retained trace digest differs from raw response")
    if row.get("trace") != parsed or row.get("errors"):
        raise ValueError("Retained trace projection differs from raw response")
    return parsed


def trace_snapshot_binding(snapshot, trace):
    """Bind completed fixture identities without treating later reads as a rescore."""
    entry = next((entry for entry in trace["entries"] if entry["citizen"] == snapshot["citizen"]), None)
    haul = snapshot.get("haul", {})
    if (entry is None or haul.get("job") != entry["job"]
            or haul.get("world") != snapshot["world"]
            or haul.get("assigned_tick") != entry["assigned_tick"]
            or haul.get("delivered_tick") != entry["delivered_tick"]
            or entry["delivered_tick"] > snapshot["tick"]):
        raise ValueError("Snapshot does not match the retained fixture citizen/job chronology")


def trace_exchanges(log):
    """Read the entire original trace-command set, including proof of absence."""
    exchanges = []
    for line in log.splitlines():
        if not line.startswith("MULTI_CITIZEN_RCON "):
            continue
        match = re.fullmatch(r"MULTI_CITIZEN_RCON id=([0-9]+) command=(.*?) response=(.*)", line)
        try:
            if match is None:
                raise ValueError("Malformed original RCON exchange")
            command = ast.literal_eval(match[2])
        except (SyntaxError, ValueError) as error:
            if TRACE_COMMAND in line:
                raise ValueError("Malformed original decision-trace exchange") from error
            continue  # Unrelated command logging is outside this provenance check.
        if command != TRACE_COMMAND:
            continue
        try:
            response = ast.literal_eval(match[3])
        except (SyntaxError, ValueError) as error:
            raise ValueError("Malformed original decision-trace response") from error
        request_id = int(match[1])
        if (not 20 <= request_id < 2 ** 31 or not isinstance(response, str)
                or line != ("MULTI_CITIZEN_RCON id=" + str(request_id) + " command="
                            + repr(command) + " response=" + repr(response))):
            raise ValueError("Original decision-trace exchange is not canonical")
        exchanges.append({"command": command, "request_id": request_id, "response": response})
    return exchanges


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


def native_witness(rcon, citizen, field, result=None):
    """Retain native bytes before validating them, including unavailable replies."""
    presence_command, data_command = native_commands(citizen, field)
    if result is None:
        result = {}
    result.update(presence_command=presence_command, presence_response=None,
                  data_command=None, data_response=None)
    presence = result["presence_response"] = rcon.run(presence_command)
    if isinstance(presence, str) and presence.strip() == "Test passed, count: 1":
        result["data_command"] = data_command
        result["data_response"] = rcon.run(data_command)
    return result


def validate_native_witness(witness, citizen, field):
    """Recognize native values and their exact UUID commands, not Sable's name.

    These are later non-atomic reads. A different value from the preceding
    snapshot may reflect actual ongoing execution and never changes the score.
    """
    presence_command, data_command = native_commands(citizen, field)
    if not isinstance(witness, dict) or witness.get("presence_command") != presence_command:
        raise ValueError("Native witness targets another citizen or field")
    if witness.get("error"):
        raise ValueError("Native witness recorded an observation error")
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


def capture(rcon, terminal_snapshot, sleep=time.sleep, retained_traces=None):
    report = {"schema": SCHEMA, "phase": PHASE, "strictly_read_only": True,
              "score_recomputed": False, "collection_atomic": False,
              "terminal_snapshot_sha256": digest(terminal_snapshot),
              "terminal_snapshot_before_sampling": copy.deepcopy(terminal_snapshot),
              "expected_citizens": EXPECTED_CITIZENS, "planned_rounds": ROUNDS,
              "interval_wall_seconds": INTERVAL_SECONDS,
              "roster_scope": ROSTER_SCOPE, "identity_source": FALLBACK_IDENTITY,
              "retained_trace_queries": [], "roster_queries": [],
              "citizens": [], "rounds": [], "errors": [],
              "status": "INCOMPLETE", "findings": []}

    def error_at(row, context, error):
        message = context + ": " + type(error).__name__ + ": " + str(error)
        row.setdefault("errors", []).append(message)
        if row is not report:
            report["errors"].append(message)

    known = set()
    trace = None
    # The recorder merely retained the response already requested by the
    # original fixture. Validation starts here, after its terminal score froze.
    if retained_traces:
        for original in retained_traces:
            row = copy.deepcopy(original)
            report["retained_trace_queries"].append(row)
            try:
                if not isinstance(row, dict):
                    raise ValueError("Retained trace record is not an object")
                row["source"] = TRACE_SOURCE
                raw = row.get("response")
                if isinstance(raw, str):
                    row["response_sha256"] = hashlib.sha256(raw.encode()).hexdigest()
                row["trace"] = trace_response(raw)
            except Exception as error:
                error_at(row if isinstance(row, dict) else report, "Retained fixture trace", error)
        try:
            trace = retained_trace(report["retained_trace_queries"])
            report["identity_source"] = TRACE_IDENTITY
        except Exception as error:
            error_at(report, "Retained fixture trace authority", error)

    transport_unavailable = False
    try:
        for x in SOURCES:
            command = f"hearthbound-colony source-readiness-audit {x} 100 1"
            row = {"source": [x, 100, 1], "command": command, "response": None}
            report["roster_queries"].append(row)
            try:
                row["response"] = rcon.run(command)
            except Exception as error:
                error_at(row, "Source roster transport", error)
                transport_unavailable = True
                break
            try:
                row["citizens"] = roster_response(row["response"], [x, 100, 1])
                known.update(row["citizens"])
            except Exception as error:
                error_at(row, "Source roster response", error)
        if trace is not None:
            report["citizens"] = sorted(entry["citizen"] for entry in trace["entries"])
            if not known.issubset(report["citizens"]):
                error_at(report, "Source roster contamination",
                         ValueError("Current source observations contain citizens outside the retained fixture trace"))
        else:
            report["citizens"] = sorted(known)
        if len(report["citizens"]) != EXPECTED_CITIZENS:
            error_at(report, "Roster coverage", ValueError("Post-window roster does not contain exactly four known citizens"))
        # A partial fallback still records known subjects. An overfull fallback
        # is ambiguous; never choose four arbitrarily or expand this cohort.
        if len(report["citizens"]) > EXPECTED_CITIZENS:
            transport_unavailable = True
        for index in range(ROUNDS):
            if transport_unavailable:
                break
            if index:
                sleep(INTERVAL_SECONDS)
            group = {"index": index, "citizens": []}
            report["rounds"].append(group)
            for citizen in report["citizens"]:
                row = {"citizen": citizen, "response": None}
                group["citizens"].append(row)
                try:
                    row["response"] = rcon.run(command_for(citizen))
                except Exception as error:
                    error_at(row, f"Round {index} citizen {citizen} transport", error)
                    transport_unavailable = True
                    break
                try:
                    snapshot = row["snapshot"] = parse_snapshot(
                        row["response"], citizen, expected_dimension="minecraft:overworld")
                    if snapshot["status"] != "OBSERVED":
                        raise ValueError("Citizen observation is unavailable: " + snapshot["status"])
                    if trace is not None:
                        trace_snapshot_binding(snapshot, trace)
                except Exception as error:
                    error_at(row, f"Round {index} citizen {citizen} snapshot", error)
                if index in (0, ROUNDS - 1):
                    # Independent native NBT witnesses, each bounded by the fixture's
                    # plain one-wheat cargo and UUID/phase scalar. They are separate
                    # server commands and may observe legitimate later transitions.
                    witnesses = row["native_haul_witnesses"] = {}
                    for field in ("jobId", "phase", "cargo"):
                        witness = witnesses[field] = {}
                        try:
                            native_witness(rcon, citizen, field, witness)
                        except Exception as error:
                            witness["error"] = type(error).__name__ + ": " + str(error)
                            error_at(row, f"Round {index} citizen {citizen} native {field} transport", error)
                            transport_unavailable = True
                            break
                        try:
                            validate_native_witness(witness, citizen, field)
                        except Exception as error:
                            witness["error"] = type(error).__name__ + ": " + str(error)
                            error_at(row, f"Round {index} citizen {citizen} native {field}", error)
                if transport_unavailable:
                    break
    except Exception as error:
        error_at(report, "Post-window collection", error)
    try:
        report["findings"] = sequence_findings(report)
        if not report["errors"]:
            report["status"] = "COMPLETE"
            world = report["rounds"][0]["citizens"][0]["snapshot"]["world"]
            validate_report(report, {"terminal_snapshot": terminal_snapshot, "world": {"world_uuid": world}})
    except (ValueError, KeyError, TypeError) as error:
        report["status"] = "INCOMPLETE"
        error_at(report, "Post-window evidence validation", error)
    return report


def validate_report(report, record):
    """Validate the separate diagnostic evidence without changing trial scoring."""
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        raise ValueError("Wrong post-window diagnostic schema")
    expected = {"phase": PHASE, "strictly_read_only": True, "score_recomputed": False,
                "collection_atomic": False, "expected_citizens": EXPECTED_CITIZENS,
                "planned_rounds": ROUNDS, "interval_wall_seconds": INTERVAL_SECONDS,
                "roster_scope": ROSTER_SCOPE}
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
    traces = report.get("retained_trace_queries")
    if not isinstance(traces, list):
        raise ValueError("Missing retained trace provenance")
    trace = retained_trace(traces) if traces else None
    identity_source = TRACE_IDENTITY if trace is not None else FALLBACK_IDENTITY
    if report.get("identity_source") != identity_source:
        raise ValueError("Citizen identity authority was replaced")
    if trace is not None and citizens != sorted(entry["citizen"] for entry in trace["entries"]):
        raise ValueError("Citizen roster differs from the retained fixture trace")
    queries = report.get("roster_queries")
    if not isinstance(queries, list) or len(queries) != len(SOURCES):
        raise ValueError("Missing roster observations")
    reconstructed = set()
    for x, row in zip(SOURCES, queries):
        if (row.get("errors") or row["source"] != [x, 100, 1]
                or row["command"] != f"hearthbound-colony source-readiness-audit {x} 100 1"):
            raise ValueError("Unexpected roster source")
        values = roster_response(row["response"], [x, 100, 1])
        if values != row["citizens"]:
            raise ValueError("Roster disagrees with raw response")
        reconstructed.update(values)
    if trace is None:
        if sorted(reconstructed) != citizens:
            raise ValueError("Citizen roster was replaced")
    elif not reconstructed.issubset(citizens):
        raise ValueError("Source observations contain foreign citizens")
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
            if row.get("errors"):
                raise ValueError("Citizen observation recorded an error")
            snapshot = parse_snapshot(row["response"], row["citizen"], world, "minecraft:overworld")
            if (snapshot != row["snapshot"] or snapshot["status"] != "OBSERVED"
                    or snapshot["world_state"] != "PRESENT"):
                raise ValueError("Snapshot differs from its actual command response")
            if trace is not None:
                trace_snapshot_binding(snapshot, trace)
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
            "identity_source": identity_source,
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
        checked = validate_report(report, record)
        # Always prove the complete source set, even when fallback claims that
        # no trace was issued. Dropping a malformed or second response must not
        # turn it into absent evidence and promote an incomplete capture.
        log_path = Path(directory) / "rcon.log"
        if log_path.is_symlink():
            raise ValueError("Trace source log is a symbolic link")
        payload = log_path.read_bytes()
        if hashlib.sha256(payload).hexdigest() != record.get("rcon_log_sha256"):
            raise ValueError("Retained trace source log digest mismatch")
        expected = [{key: query[key] for key in ("command", "request_id", "response")}
                    for query in report["retained_trace_queries"]]
        if trace_exchanges(payload.decode("utf-8")) != expected:
            raise ValueError("Retained traces differ from the complete original RCON trace-command set")
        checked["retained_trace_source_log_verified"] = True
        return checked
    except (OSError, ValueError, KeyError, TypeError, AttributeError, OverflowError, RecursionError) as error:
        return {"status": "INVALID_DIAGNOSTIC_EVIDENCE", "findings": [],
                "error": type(error).__name__ + ": " + str(error)}
