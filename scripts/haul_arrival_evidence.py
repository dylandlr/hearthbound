#!/usr/bin/env python3
"""Validate native insertion observations; never move an actor or grant rewards.

The existing chest smoke has one declared transfer, source 8->7 and destination
0->1. Its arrival is evaluated at that insertion, with both original geometries.
A later pose is a separate observation and cannot repair an invalid insertion.
"""
from copy import deepcopy
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import subprocess
from uuid import UUID

PREFIX = "HAUL_ARRIVAL_V1 "
SCHEMA = "hearthbound.haul-arrival.v1"
SOURCE = [3, 100, 1]
DESTINATION = [7, 100, 1]
MOTOR_REACH_SQ = 6.25
SMOKE_REACH_SQ = 2.6 * 2.6
MAX_RESPONSE_BYTES = 3900
TRANSFER_QUERY = 'execute if data block 7 100 1 Items[{id:"minecraft:wheat",Count:1b}]'
SOURCE_QUERY = 'execute if data block 3 100 1 Items[{id:"minecraft:wheat",Count:7b}]'
BINDING_KEYS = {"world", "session", "dimension", "citizen", "job", "assigned_tick",
                "source", "destination"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def test_passed(text):
    return type(text) is str and re.fullmatch(r"test passed(?:, count: 1)?", text.strip().lower()) is not None


def canonical_uuid(value):
    require(type(value) is str and str(UUID(value)) == value, "Invalid canonical UUID")
    return value


def integer(value, label):
    require(type(value) is int and 0 <= value < 2**63, "Invalid integer: " + label)


def vector(value, label, integral=False):
    require(type(value) is list and len(value) == 3, "Invalid vector: " + label)
    for component in value:
        require(type(component) is int if integral else type(component) in (int, float),
                "Invalid vector type: " + label)
        require(math.isfinite(component) and abs(component) <= 30_000_000,
                "Nonfinite or out-of-world vector: " + label)


def distances(position, destination):
    vector(position, "position")
    vector(destination, "destination", integral=True)
    dx = position[0] - (destination[0] + .5)
    dz = position[2] - (destination[2] + .5)
    motor_dy = position[1] - (destination[1] + .5)
    smoke_dy = position[1] - destination[1]
    return (dx * dx + motor_dy * motor_dy + dz * dz,
            dx * dx + smoke_dy * smoke_dy + dz * dz)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "Duplicate JSON field: " + key)
        value[key] = item
    return value


def _nonfinite(value):
    raise ValueError("Nonfinite JSON constant: " + value)


def parse_response(text):
    require(type(text) is str and len(text.encode()) <= MAX_RESPONSE_BYTES,
            "Missing or oversized arrival response")
    text = text.strip()
    require(text.startswith(PREFIX), "Missing native arrival prefix")
    value = json.loads(text[len(PREFIX):], object_pairs_hook=_unique_object,
                       parse_constant=_nonfinite)
    require(type(value) is dict and value.get("schema") == SCHEMA,
            "Wrong arrival schema")
    require(value.get("status") == "OBSERVED", "Native arrival observation unavailable")
    return value


def validate_binding(binding):
    require(type(binding) is dict and set(binding) == BINDING_KEYS,
            "Missing or extra assignment binding fields")
    for name in ("world", "session", "citizen", "job"):
        canonical_uuid(binding[name])
    require(binding["dimension"] == "minecraft:overworld", "Foreign dimension")
    integer(binding["assigned_tick"], "assigned_tick")
    vector(binding["source"], "source", integral=True)
    vector(binding["destination"], "destination", integral=True)
    require(binding["source"] == SOURCE and binding["destination"] == DESTINATION,
            "Foreign fixture endpoints")


def inventory(value, label):
    require(type(value) is dict and value.get("status") == "OBSERVED"
            and value.get("scope") == "LOCAL_VANILLA_CONTAINER_NBT"
            and value.get("complete") is True, "Native container unavailable: " + label)
    for name in ("slots", "inspected_slots", "wheat", "total_items"):
        integer(value.get(name), label + "." + name)
    require(value["slots"] == value["inspected_slots"] == 27,
            "Fixture is not a complete local chest: " + label)
    require(value["wheat"] <= value["total_items"] <= 27 * 127,
            "Inconsistent native item count: " + label)


def sample(value, binding, label):
    require(type(value) is dict, "Missing native sample: " + label)
    integer(value.get("tick"), label + ".tick")
    vector(value.get("position"), label + ".position")
    computed = distances(value["position"], binding["destination"])
    for name, distance in zip(("motor_distance_sq", "smoke_distance_sq"), computed):
        claimed = value.get(name)
        require(type(claimed) in (int, float) and math.isfinite(claimed)
                and math.isclose(claimed, distance, rel_tol=1e-12, abs_tol=1e-12),
                "Native distance disagrees with coordinates: " + label)
    inventory(value.get("source"), label + ".source")
    inventory(value.get("destination"), label + ".destination")
    return computed


def validate_snapshot(value, binding):
    validate_binding(binding)
    require(type(value) is dict, "Missing native snapshot")
    require(value.get("schema") == SCHEMA and value.get("status") == "OBSERVED",
            "Native arrival observation unavailable")
    validate_binding(value.get("binding"))
    require(value["binding"] == binding, "Foreign or stale job binding")
    for name in ("world", "session", "dimension", "citizen"):
        require(value.get(name) == binding[name], "Foreign current " + name)
    require(value.get("observation_scope") == "LOCAL_VANILLA_CONTAINER_NBT"
            and value.get("reward_authorized") is False, "Invalid observation scope/authority")
    integer(value.get("tick"), "query_tick")
    require(value["tick"] >= binding["assigned_tick"], "Query predates assignment")
    require(type(value.get("phase")) is int and 0 <= value["phase"] <= 6,
            "Invalid native job phase")
    require(type(value.get("cargo_present")) is bool, "Invalid cargo-presence observation")
    if value.get("delivered_tick") is not None:
        integer(value["delivered_tick"], "delivered_tick")
        require(binding["assigned_tick"] <= value["delivered_tick"] <= value["tick"],
                "Invalid delivered tick chronology")
    current = sample(value.get("current"), binding, "current")
    require(value["current"]["tick"] == value["tick"], "Non-atomic current snapshot")
    return current


def verify_delivery(value, binding):
    """Recompute geometry/conservation from raw samples, not native booleans."""
    current_distances = validate_snapshot(value, binding)
    require(value["phase"] == 2 and value["cargo_present"] is False,
            "The exact job is not completed without cargo")
    witness = value.get("witness")
    require(type(witness) is dict and witness.get("status") == "OBSERVED",
            "Native insertion witness missing or unavailable")
    validate_binding(witness.get("binding"))
    require(witness["binding"] == binding, "Foreign insertion binding")
    require(witness.get("cargo") == {"item": "minecraft:wheat", "count": 1}
            and type(witness["cargo"]["count"]) is int, "Invalid observed insertion cargo")
    before, after = witness.get("before"), witness.get("after")
    before_distances = sample(before, binding, "before")
    after_distances = sample(after, binding, "after")
    require(binding["assigned_tick"] <= before["tick"] == after["tick"]
            == value.get("delivered_tick") <= value["tick"],
            "Insertion samples are not the same completed action tick")
    for label, observed in (("before", before_distances), ("after", after_distances)):
        require(observed[0] <= MOTOR_REACH_SQ, "Insertion outside motor radius: " + label)
        require(observed[1] <= SMOKE_REACH_SQ, "Insertion outside smoke radius: " + label)
    for label, observed, source, destination in (
        ("before", before, 7, 0), ("after", after, 7, 1),
        ("current", value["current"], 7, 1),
    ):
        require(observed["source"]["wheat"] == observed["source"]["total_items"] == source,
                "Native source inventory mismatch: " + label)
        require(observed["destination"]["wheat"] == observed["destination"]["total_items"]
                == destination, "Native destination inventory mismatch: " + label)
    return {"insertion_tick": after["tick"], "query_tick": value["tick"],
            "before_motor_distance_sq": before_distances[0],
            "before_smoke_distance_sq": before_distances[1],
            "after_motor_distance_sq": after_distances[0],
            "after_smoke_distance_sq": after_distances[1],
            "later_motor_distance_sq": current_distances[0],
            "later_smoke_distance_sq": current_distances[1],
            "later_snapshot_within_smoke_radius": current_distances[1] <= SMOKE_REACH_SQ,
            "later_position_differs": value["current"]["position"] != after["position"],
            "physical_inventory_verified": True, "arrival_verified_at_insertion": True,
            "exactly_once_or_crash_atomic_claimed": False, "reward_authorized": False}


def native_uuid(text):
    matches = re.findall(r"\[I;\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),\s*(-?\d+)\]", text)
    require(len(matches) == 1, "Native UUID absent or ambiguous")
    parts = [int(part) for part in matches[0]]
    require(all(-(2**31) <= part < 2**31 for part in parts), "Invalid native UUID component")
    return str(UUID(int=sum((part & 0xffffffff) << (96 - 32 * index)
                           for index, part in enumerate(parts))))


def provenance():
    repo = Path(__file__).resolve().parents[1]
    try:
        checked_out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo,
                                             text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        checked_out = None
    fields = {name: os.environ.get(name) for name in (
        "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB", "GITHUB_SHA",
        "HEARTHBOUND_TRIAL_MODE", "HEARTHBOUND_WORLD_SEED", "HEARTHBOUND_RESOURCE_SCHEDULE",
        "HEARTHBOUND_ATTENTION_MODE", "HEARTHBOUND_ATTENTION_CHALLENGE", "HEARTHBOUND_MATRIX_SLOT")}
    head = None
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if event_path:
        try:
            head = json.loads(Path(event_path).read_text()).get("pull_request", {}).get("head", {}).get("sha")
        except (OSError, ValueError, AttributeError):
            pass
    names = ("scripts/rcon_smoke.py", "scripts/haul_arrival_evidence.py", "scripts/haul_smoke_diagnostics.py",
             ".github/workflows/dedicated-server-smoke.yml",
             "src/main/java/dev/hearthbound/world/HaulArrivalWitness.java",
             "src/main/java/dev/hearthbound/world/SableHauling.java",
             "src/main/java/dev/hearthbound/world/SableController.java",
             "src/main/java/dev/hearthbound/world/HaulMotorDiagnostics.java",
             "src/main/java/dev/hearthbound/world/SourceReportSession.java",
             "src/main/java/dev/hearthbound/world/HearthboundWorldIdentity.java",
             "src/main/java/dev/hearthbound/evidence/HaulArrivalGeometry.java")
    return {"checked_out_sha": checked_out, "pull_request_head_sha": head,
            "context": fields, "source_sha256": {
                name: hashlib.sha256((repo / name).read_bytes()).hexdigest() for name in names},
            "behavioral_retries_allowed": 0}


class ArrivalEvidence:
    """Persist raw responses even when parsing or acceptance fails."""
    def __init__(self, path, metadata=None):
        self.path = Path(path)
        self.binding = None
        self.data = {"schema": "hearthbound.haul-arrival-acceptance.v1", "status": "NOT_RUN",
                     "provenance": provenance() if metadata is None else metadata,
                     "source": SOURCE, "destination": DESTINATION,
                     "responses": [], "transfer_responses": [], "failure_diagnostics": [],
                     "original_failure_cause_established": False,
                     "neural_policy_improvement_claimed": False}
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.data, sort_keys=True, indent=2, allow_nan=False) + "\n")

    def read(self, command, request_id, query, label):
        row = {"label": label, "request_id": request_id, "command": query}
        self.data["responses"].append(row)
        try:
            response_id, output = command(request_id, query)
            row.update(response_id=response_id, response=output)
            require(type(request_id) is int and type(response_id) is int
                    and response_id == request_id, "Arrival RCON response ID mismatch")
            return output
        except Exception as error:
            row["error"] = type(error).__name__ + ": " + str(error)
            raise
        finally:
            self.save()

    def bind(self, command, audit):
        try:
            self.data["assignment_audit"] = audit
            output = self.read(command, 94,
                "data get entity @e[type=minecraft:villager,name=Sable,limit=1] UUID", "native_uuid")
            citizen = native_uuid(output)
            jobs = re.findall(r"\bAUDIT job=([0-9a-f-]{36})\b", audit)
            require(len(jobs) == 1, "Audit job identity missing or ambiguous")
            job = canonical_uuid(jobs[0])
            value = parse_response(self.read(command, 95,
                "hearthbound-haul-arrival " + citizen, "assignment"))
            binding = value.get("binding")
            validate_binding(binding)
            require(binding["citizen"] == citizen and binding["job"] == job,
                    "Native assignment identity differs from issued job")
            validate_snapshot(value, binding)
            self.binding = deepcopy(binding)
            self.data.update(binding=self.binding, status="RUNNING")
            self.save()
        except Exception as error:
            self.fail(command, error)
            raise

    def record_transfer(self, polls, transferred):
        self.data["transfer_poll"] = {"polls": polls, "transferred": transferred}
        self.save()

    def record_poll(self, request_id, response_id, query, output):
        if query == TRANSFER_QUERY and 100 <= request_id < 175:
            self.data["transfer_responses"].append({"request_id": request_id,
                "response_id": response_id, "command": query, "response": output})
            self.save()

    def record_source_check(self, response_id, output):
        self.data["source_count_check"] = {"request_id": 300, "response_id": response_id, "command": SOURCE_QUERY,
            "response": output, "passed": type(response_id) is int and response_id == 300 and test_passed(output)}
        self.save()

    def check_delivery(self, command):
        try:
            require(self.binding is not None, "Assignment not bound before polling")
            transfer = self.data.get("transfer_poll", {})
            require(transfer.get("transferred") is True and type(transfer.get("polls")) is int
                    and 1 <= transfer["polls"] <= 75,
                    "Existing physical destination poll did not pass")
            require(self.data.get("source_count_check", {}).get("passed") is True,
                    "Existing physical source assertion did not pass")
            citizen = self.binding["citizen"]
            later = self.read(command, 301,
                f"execute as {citizen} positioned 7.5 100 1.5 if entity @s[distance=..2.6]",
                "later_proximity_query")
            require(later.strip().lower() == "test failed"
                    or test_passed(later),
                    "Unrecognized later proximity response")
            self.read(command, 302, "hearthbound-haul-arrival " + citizen, "post_transfer")
            result = replay_evidence(dict(self.data, status="PASSED"))
            self.data.update(status="PASSED", validation=result)
            self.save()
            return result
        except Exception as error:
            self.fail(command, error)
            raise

    def fail(self, command, error):
        self.data.update(status="FAILED", error=type(error).__name__ + ": " + str(error))
        # No retry or intervention. An exact-UUID native snapshot retains pose,
        # phase and both inventories, including on the original proximity path.
        if self.binding is not None:
            citizen = self.binding["citizen"]
            queries = ("hearthbound-haul-arrival " + citizen,
                       "data get entity " + citizen + " Pos",
                       "execute at " + citizen + " run sable haul-audit",
                       "data get block 3 100 1 Items", "data get block 7 100 1 Items")
            for request_id, query in enumerate(queries, 704):
                row = {"request_id": request_id, "command": query}
                try:
                    response_id, output = command(request_id, query)
                    row.update(response_id=response_id, response=output,
                               response_id_matches=response_id == request_id)
                except Exception as diagnostic_error:
                    row["error"] = type(diagnostic_error).__name__ + ": " + str(diagnostic_error)
                self.data["failure_diagnostics"].append(row)
        self.save()


def replay_evidence(document, expected_checkout_sha=None):
    """Re-evaluate retained native responses without trusting cached validation."""
    require(type(document) is dict and document.get("schema") == "hearthbound.haul-arrival-acceptance.v1",
            "Wrong acceptance artifact schema")
    require(document.get("status") == "PASSED", "Native trial did not pass")
    if expected_checkout_sha is not None:
        require(type(expected_checkout_sha) is str and re.fullmatch("[0-9a-f]{40}", expected_checkout_sha),
                "Expected checkout SHA must be exact")
        require(document.get("provenance", {}).get("checked_out_sha") == expected_checkout_sha,
                "Foreign checked-out source SHA")
    rows = document.get("responses")
    require(type(rows) is list and len(rows) == 4, "Missing or duplicate native response records")
    records = {}
    for row in rows:
        require(type(row) is dict and row.get("label") not in records, "Duplicate response label")
        require(type(row.get("request_id")) is int and type(row.get("response_id")) is int
                and row["response_id"] == row["request_id"],
                "Native response identity mismatch")
        require("error" not in row, "Native response contains an error")
        records[row.get("label")] = row
    require(set(records) == {"native_uuid", "assignment", "later_proximity_query", "post_transfer"},
            "Missing native response stage")
    citizen = native_uuid(records["native_uuid"].get("response", ""))
    initial = parse_response(records["assignment"].get("response"))
    binding = initial.get("binding")
    validate_binding(binding)
    require(binding == document.get("binding") and binding["citizen"] == citizen,
            "Retained assignment binding mismatch")
    jobs = re.findall(r"\bAUDIT job=([0-9a-f-]{36})\b", document.get("assignment_audit", ""))
    require(jobs == [binding["job"]], "Retained assignment audit mismatch")
    validate_snapshot(initial, binding)
    expected_queries = {
        "native_uuid": (94, "data get entity @e[type=minecraft:villager,name=Sable,limit=1] UUID"),
        "assignment": (95, "hearthbound-haul-arrival " + citizen),
        "later_proximity_query": (301, f"execute as {citizen} positioned 7.5 100 1.5 if entity @s[distance=..2.6]"),
        "post_transfer": (302, "hearthbound-haul-arrival " + citizen),
    }
    for name, (request_id, query) in expected_queries.items():
        require(records[name]["request_id"] == request_id and records[name].get("command") == query,
                "Foreign native query: " + name)
    transfer = document.get("transfer_poll", {})
    polls = document.get("transfer_responses")
    require(transfer.get("transferred") is True and type(transfer.get("polls")) is int
            and 1 <= transfer["polls"] <= 75 and type(polls) is list and len(polls) == transfer["polls"],
            "Missing physical transfer poll observations")
    for index, row in enumerate(polls):
        require(type(row.get("request_id")) is int and type(row.get("response_id")) is int
                and row["request_id"] == row["response_id"] == 100 + index
                and row.get("command") == TRANSFER_QUERY, "Foreign physical transfer query")
        raw = row.get("response", "")
        require(type(raw) is str and (raw.strip().lower() == "test failed" or test_passed(raw)),
                "Unrecognized physical transfer response")
        passed = test_passed(raw)
        require(passed is (index == len(polls) - 1), "Invalid physical transfer poll sequence")
    source = document.get("source_count_check", {})
    require(type(source.get("request_id")) is int and type(source.get("response_id")) is int
            and source["request_id"] == source["response_id"] == 300
            and source.get("command") == SOURCE_QUERY
            and test_passed(source.get("response")), "Native source assertion failed")
    final = parse_response(records["post_transfer"].get("response"))
    result = verify_delivery(final, binding)
    require(final["tick"] >= initial["tick"], "Final arrival query predates initial binding query")
    later = records["later_proximity_query"].get("response", "").strip().lower()
    require(later == "test failed" or test_passed(later), "Invalid later proximity response")
    result["later_query_within_smoke_radius"] = test_passed(later)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--expected-checkout-sha")
    args = parser.parse_args()
    raw = args.evidence.read_bytes()
    document = json.loads(raw, object_pairs_hook=_unique_object,
                          parse_constant=_nonfinite)
    result = replay_evidence(document, args.expected_checkout_sha)
    print(json.dumps({"schema": "hearthbound.haul-arrival-replay.v1", "status": "PASSED",
        "evidence_sha256": hashlib.sha256(raw).hexdigest(),
        "binding": document["binding"], "validation": result}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
