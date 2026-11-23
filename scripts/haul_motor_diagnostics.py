#!/usr/bin/env python3
"""Validate bounded, read-only motor snapshots without granting action authority."""
import json
import math
from uuid import UUID

COMMAND = "hearthbound-haul-diagnostics"
PREFIX = "HAUL_MOTOR_DIAGNOSTICS_V1 "
SCHEMA = "hearthbound.haul-motor-diagnostics.v1"
MAX_RESPONSE_BYTES = 3900
STATUSES = {"OBSERVED", "NOT_LOADED_IN_DIMENSION", "NOT_A_MARKED_VILLAGER", "INVALID_UUID",
            "OVERSIZED_UNAVAILABLE", "SNAPSHOT_UNAVAILABLE", "OBSERVATION_SIDE_EFFECT_DETECTED"}
READ_ONLY_CHECKS = {"persistent_nbt_unchanged", "path_identity_unchanged", "path_index_unchanged",
                    "claim_unchanged", "tick_count_unchanged", "position_unchanged",
                    "velocity_unchanged", "no_ai_unchanged"}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical_uuid(value):
    require(isinstance(value, str), "UUID must be a string")
    require(str(UUID(value)) == value, "UUID must be canonical lowercase text")
    return value


def command_for(citizen):
    return COMMAND + " " + canonical_uuid(citizen)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field: " + key)
        result[key] = value
    return result


def _finite_constant(value):
    raise ValueError("Nonfinite JSON constant: " + value)


def _integer(value, name, minimum=0, nullable=False):
    if nullable and value is None:
        return
    require(type(value) is int and value >= minimum, "Invalid integer: " + name)


def _vector(value, name, integral=False, nullable=False, length=3):
    if nullable and value is None:
        return
    require(isinstance(value, list) and len(value) == length, "Invalid vector: " + name)
    for number in value:
        require(type(number) is int if integral else type(number) in (int, float),
                "Invalid vector component: " + name)
        require(abs(number) <= 1e100 and math.isfinite(number), "Nonfinite or oversized vector: " + name)


def _boolean(value, name):
    require(type(value) is bool, "Invalid boolean: " + name)


def _keys(value, names, label):
    require(isinstance(value, dict) and set(names) <= set(value), "Missing fields in " + label)


def validate_snapshot(snapshot, expected_citizen=None, expected_world=None,
                      expected_dimension=None):
    """Accept diagnostic anomalies as observations; reject malformed evidence.

    A foreign claim, malformed haul tag, unloaded endpoint, or unfinished path
    remains visible in a valid snapshot. This function never turns those facts
    into a completion, repair request, or explanation of why a citizen stalled.
    """
    require(isinstance(snapshot, dict), "Snapshot must be an object")
    _keys(snapshot, ("schema", "status", "world", "world_state", "dimension", "dimension_available",
                     "tick", "citizen", "loaded", "strictly_read_only", "atomic", "policy_control",
                     "reward_authorized"), "snapshot")
    require(snapshot.get("schema") == SCHEMA, "Wrong motor diagnostic schema")
    status = snapshot.get("status")
    require(status in STATUSES, "Unknown motor diagnostic status")
    require(snapshot["atomic"] is True, "Diagnostic snapshot is not atomic")
    require(snapshot["strictly_read_only"] is (status != "OBSERVATION_SIDE_EFFECT_DETECTED"),
            "Read-only status disagrees with recorded side effect")
    for name in ("policy_control", "reward_authorized"):
        require(snapshot.get(name) is False, "Diagnostic granted authority: " + name)
    _integer(snapshot.get("tick"), "tick")
    _boolean(snapshot["dimension_available"], "dimension_available")
    if snapshot["dimension_available"]:
        require(isinstance(snapshot.get("dimension"), str) and ":" in snapshot["dimension"], "Missing dimension")
    else:
        require(snapshot["dimension"] is None, "Unavailable dimension contains a value")
    if expected_dimension is not None:
        require(snapshot["dimension"] == expected_dimension, "Foreign dimension")
    require(snapshot.get("world_state") in ("PRESENT", "ABSENT", "UNAVAILABLE"), "Invalid world identity state")
    if snapshot["world_state"] == "PRESENT":
        canonical_uuid(snapshot.get("world"))
    else:
        require(snapshot.get("world") is None, "Absent identity contains a UUID")
    if expected_world is not None:
        require(snapshot.get("world") == canonical_uuid(expected_world), "Foreign world")
    if status == "INVALID_UUID":
        require(snapshot.get("citizen") is None and snapshot.get("loaded") is False,
                "Invalid UUID response selected an entity")
        require(expected_citizen is None, "Invalid UUID response for an expected citizen")
        return snapshot
    canonical_uuid(snapshot.get("citizen"))
    if expected_citizen is not None:
        require(snapshot["citizen"] == canonical_uuid(expected_citizen), "Foreign citizen")
    _boolean(snapshot.get("loaded"), "loaded")
    if status != "OBSERVED":
        if status in ("NOT_LOADED_IN_DIMENSION", "NOT_A_MARKED_VILLAGER"):
            require(snapshot["loaded"] is (status == "NOT_A_MARKED_VILLAGER"),
                    "Entity presence disagrees with diagnostic status")
            require(not any(key in snapshot for key in ("haul", "claim", "motor", "navigation")),
                    "Rejected entity exposed a worker snapshot")
        return snapshot
    require(snapshot["loaded"] is True, "Observed citizen is not loaded")
    require(snapshot.get("observation_scope") == "NAMED_MOTOR_AUTHORITY_INVARIANTS",
            "Unknown diagnostic observation scope")
    require(snapshot.get("invariant_baseline") == "AFTER_NATIVE_ENTITY_SERIALIZATION",
            "Unknown read-only invariant baseline")
    entity = snapshot.get("entity")
    require(isinstance(entity, dict), "Missing entity snapshot")
    _keys(entity, ("alive", "no_ai", "can_update", "tick_count", "position", "velocity", "on_ground",
                   "horizontal_collision", "chunk", "chunk_loaded", "forced_chunk", "position_entity_ticking",
                   "sable_marker", "citizen_marker", "private_trial_marker"), "entity")
    for name in ("alive", "no_ai", "on_ground", "horizontal_collision", "can_update",
                 "sable_marker", "citizen_marker", "private_trial_marker"):
        _boolean(entity.get(name), "entity." + name)
    require(entity["sable_marker"] or entity["citizen_marker"], "Observed entity has no worker marker")
    _vector(entity.get("position"), "entity.position")
    _vector(entity.get("velocity"), "entity.velocity")
    _integer(entity.get("tick_count"), "entity.tick_count")
    _vector(entity.get("chunk"), "entity.chunk", integral=True, length=2)
    for name in ("chunk_loaded", "forced_chunk", "position_entity_ticking"):
        _boolean(entity.get(name), "entity." + name)
    require(entity["chunk_loaded"] is True, "Loaded entity has no loaded chunk")
    haul = snapshot.get("haul")
    require(isinstance(haul, dict) and isinstance(haul.get("types"), dict), "Missing typed haul snapshot")
    _keys(haul, ("present", "type", "types", "phase", "phase_name", "job", "world", "source", "destination",
                 "assigned_tick", "delivered_tick", "error", "error_truncated", "cargo"), "haul")
    _boolean(haul.get("present"), "haul.present")
    require(type(haul["type"]) is int and 0 <= haul["type"] <= 12, "Invalid haul tag type")
    for name in ("phase", "source", "destination", "jobId", "colonyWorldId", "assignedTick",
                 "physicalDeliveredTick", "cargo", "error"):
        kind = haul["types"].get(name)
        require(type(kind) is int and 0 <= kind <= 12, "Invalid NBT type: " + name)
    if haul.get("phase") is not None:
        require(type(haul["phase"]) is int and haul["types"]["phase"] == 3,
                "Phase is not backed by an integer tag")
    require(isinstance(haul.get("phase_name"), str), "Missing phase classification")
    for name in ("job", "world"):
        if haul.get(name) is not None:
            canonical_uuid(haul[name])
    for name in ("source", "destination"):
        _vector(haul.get(name), "haul." + name, integral=True, nullable=True)
        require((haul[name] is not None) == (haul["types"][name] == 4),
                "Coordinate is not backed by a long tag: " + name)
    for name in ("assigned_tick", "delivered_tick"):
        value = haul.get(name)
        require(value is None or type(value) is int, "Invalid retained tick: " + name)
    require(haul["error"] is None or isinstance(haul["error"], str) and len(haul["error"]) <= 1024,
            "Unbounded or missing haul error")
    _boolean(haul.get("error_truncated"), "haul.error_truncated")
    cargo = haul.get("cargo")
    require(isinstance(cargo, dict), "Missing cargo snapshot")
    _keys(cargo, ("present", "type", "item", "count", "empty", "item_truncated"), "cargo")
    _boolean(cargo["item_truncated"], "cargo.item_truncated")
    _boolean(cargo.get("present"), "cargo.present")
    require(type(cargo.get("type")) is int and 0 <= cargo["type"] <= 12,
            "Invalid cargo tag type")
    require(cargo["type"] == haul["types"]["cargo"], "Cargo tag type mismatch")
    if not cargo["present"] or cargo["type"] != 10:
        require(all(cargo.get(name) is None for name in ("item", "count", "empty")),
                "Absent or malformed cargo was decoded as inventory")
    else:
        require(cargo["item"] is None or isinstance(cargo["item"], str), "Invalid retained cargo item ID")
        require(cargo["count"] is None or type(cargo["count"]) is int, "Invalid retained cargo count")
        if cargo["item"] is None or cargo["count"] is None:
            require(cargo["empty"] is None, "Malformed cargo has an inferred emptiness value")
        else:
            require(cargo["empty"] is (cargo["count"] <= 0 or cargo["item"] == "minecraft:air"),
                    "Cargo emptiness disagrees with retained fields")
    claim = snapshot.get("claim")
    require(isinstance(claim, dict), "Missing claim snapshot")
    _keys(claim, ("store_present", "source_owner", "owned_by_citizen", "total_claims"), "claim")
    _boolean(claim.get("store_present"), "claim.store_present")
    if claim.get("source_owner") is not None:
        canonical_uuid(claim["source_owner"])
    if claim["store_present"] and haul["source"] is not None:
        require(claim["owned_by_citizen"] is (claim.get("source_owner") == snapshot["citizen"]),
                "Claim ownership identity mismatch")
    else:
        require(claim["owned_by_citizen"] is None, "Unavailable claim ownership was inferred")
    _integer(claim.get("total_claims"), "claim.total_claims", nullable=True)
    motor = snapshot.get("motor")
    require(isinstance(motor, dict), "Missing motor snapshot")
    _keys(motor, ("active", "phase_known", "paused", "quarantined", "intended_target", "reach_sq",
                  "target_chunk_loaded", "distance_target", "navigation_request_target", "distance_sq",
                  "within_reach"), "motor")
    _boolean(motor.get("active"), "motor.active")
    _vector(motor.get("intended_target"), "motor.intended_target", integral=True, nullable=True)
    _vector(motor.get("distance_target"), "motor.distance_target", nullable=True)
    _vector(motor.get("navigation_request_target"), "motor.navigation_request_target", nullable=True)
    for name in ("phase_known", "paused", "quarantined"):
        _boolean(motor.get(name), "motor." + name)
    require(motor.get("reach_sq") == 6.25, "Motor reach threshold changed")
    distance = motor.get("distance_sq")
    if distance is not None:
        require(type(distance) in (int, float) and 0 <= distance <= 1e201 and math.isfinite(distance),
                "Invalid motor distance")
        require(motor.get("within_reach") is (distance <= 6.25), "Reach comparison disagrees with distance")
    else:
        require(motor.get("within_reach") is None, "Unknown target has a reach result")
    if motor.get("target_chunk_loaded") is not None:
        _boolean(motor["target_chunk_loaded"], "motor.target_chunk_loaded")
    expected_target = haul["source"] if haul["phase"] == 0 else haul["destination"] if haul["phase"] == 1 else None
    require(motor["intended_target"] == expected_target, "Motor target differs from typed phase/endpoints")
    if expected_target is None:
        require(all(motor[name] is None for name in ("distance_target", "navigation_request_target",
                                                     "distance_sq", "within_reach", "target_chunk_loaded")),
                "Absent motor target has inferred geometry")
    else:
        x, y, z = expected_target
        require(motor["distance_target"] == [x + .5, y + .5, z + .5]
                and motor["navigation_request_target"] == [x + .5, y, z + .5],
                "Motor distance/navigation target geometry changed")
        expected_distance = sum((a - b) ** 2 for a, b in zip(entity["position"], motor["distance_target"]))
        require(distance is not None and math.isclose(distance, expected_distance, rel_tol=1e-9, abs_tol=1e-9),
                "Motor distance differs from observed position")
    navigation = snapshot.get("navigation")
    require(isinstance(navigation, dict), "Missing navigation snapshot")
    _keys(navigation, ("done", "stuck", "target", "path_present", "next_node_index", "node_count",
                       "path_can_reach", "path_target", "next_node", "end_node"), "navigation")
    _boolean(navigation.get("done"), "navigation.done")
    _boolean(navigation.get("stuck"), "navigation.stuck")
    _boolean(navigation.get("path_present"), "navigation.path_present")
    for name in ("target", "path_target", "next_node", "end_node"):
        _vector(navigation.get(name), "navigation." + name, integral=True, nullable=True)
    for name in ("next_node_index", "node_count"):
        _integer(navigation.get(name), "navigation." + name, nullable=True)
    if navigation.get("path_can_reach") is not None:
        _boolean(navigation["path_can_reach"], "navigation.path_can_reach")
    if navigation["path_present"]:
        require(type(navigation.get("node_count")) is int
                and type(navigation.get("next_node_index")) is int
                and navigation["next_node_index"] <= navigation["node_count"], "Invalid existing path cursor")
    inventories = snapshot.get("inventories")
    require(isinstance(inventories, dict), "Missing endpoint inventories")
    for endpoint in ("source", "destination"):
        inventory = inventories.get(endpoint)
        require(isinstance(inventory, dict) and isinstance(inventory.get("status"), str),
                "Missing inventory status: " + endpoint)
        _keys(inventory, ("status", "scope", "slots", "inspected_slots", "wheat", "total_items", "complete"),
              "inventory." + endpoint)
        _boolean(inventory.get("complete"), endpoint + ".complete")
        for name in ("slots", "inspected_slots", "wheat", "total_items"):
            _integer(inventory.get(name), endpoint + "." + name, nullable=True)
        if inventory.get("slots") is not None and inventory.get("inspected_slots") is not None:
            require(inventory["inspected_slots"] <= inventory["slots"], "Inventory inspection exceeds slots")
        if inventory["complete"]:
            require(inventory["status"] == "OBSERVED" and type(inventory["slots"]) is int
                    and inventory["slots"] == inventory["inspected_slots"] <= 64
                    and type(inventory["wheat"]) is int and type(inventory["total_items"]) is int
                    and inventory["wheat"] <= inventory["total_items"], "Complete inventory witness is inconsistent")
    checks = snapshot.get("read_only_checks")
    require(isinstance(checks, dict) and READ_ONLY_CHECKS <= set(checks)
            and all(value is True for value in checks.values()), "Snapshot inspection mutated tracked state")
    return snapshot


def parse_snapshot(response, expected_citizen=None, expected_world=None, expected_dimension=None):
    require(isinstance(response, str) and len(response.encode("utf-8")) <= MAX_RESPONSE_BYTES,
            "Oversized or nontext diagnostic response")
    response = response.strip()
    require(response.startswith(PREFIX), "Missing motor diagnostic prefix")
    snapshot = json.loads(response[len(PREFIX):], object_pairs_hook=_unique_object,
                          parse_constant=_finite_constant)
    return validate_snapshot(snapshot, expected_citizen, expected_world, expected_dimension)


def capture_snapshot(rcon, citizen, expected_world=None, expected_dimension=None):
    return parse_snapshot(rcon.run(command_for(citizen)), citizen, expected_world, expected_dimension)


def authority_view(snapshot):
    """Stable fields for repeated blocked-job reads; positions and paths may tick."""
    validate_snapshot(snapshot)
    require(snapshot["status"] == "OBSERVED", "No loaded worker authority to compare")
    return {name: snapshot[name] for name in ("world", "dimension", "citizen", "haul", "claim", "inventories")}


def require_blocked_cargo(snapshot, citizen, source, destination):
    validate_snapshot(snapshot, citizen)
    require(snapshot["status"] == "OBSERVED", "Blocked worker is not observable")
    haul, motor, claim = snapshot["haul"], snapshot["motor"], snapshot["claim"]
    require(haul["phase"] == 1 and haul["job"] is not None
            and haul["source"] == list(source) and haul["destination"] == list(destination),
            "Blocked worker has the wrong physical assignment")
    require(haul["cargo"]["present"] and haul["cargo"]["item"] == "minecraft:wheat"
            and haul["cargo"]["count"] == 1 and haul["cargo"]["empty"] is False,
            "Blocked worker did not retain one actual wheat")
    require(claim["owned_by_citizen"] is True and motor["active"] is True
            and motor["intended_target"] == list(destination)
            and motor["target_chunk_loaded"] is True and motor["within_reach"] is False,
            "Blocked job lacks its claim or lies within delivery reach")
    for endpoint, count in (("source", 7), ("destination", 0)):
        inventory = snapshot["inventories"][endpoint]
        require(inventory["complete"] is True and inventory["wheat"] == count,
                "Blocked endpoint inventory mismatch: " + endpoint)
    return haul["job"]


def require_completed(snapshot, citizen, job, source, destination):
    validate_snapshot(snapshot, citizen)
    require(snapshot["status"] == "OBSERVED", "Completed worker is not observable")
    haul = snapshot["haul"]
    require(haul["job"] == canonical_uuid(job) and haul["phase"] == 2
            and haul["source"] == list(source) and haul["destination"] == list(destination)
            and type(haul["assigned_tick"]) is int and type(haul["delivered_tick"]) is int
            and 0 <= haul["assigned_tick"] <= haul["delivered_tick"] <= snapshot["tick"],
            "Completed job provenance does not match")
    require(haul["cargo"]["present"] is False and snapshot["motor"]["active"] is False
            and snapshot["claim"]["source_owner"] is None, "Completion left cargo, active motor, or a claim")
    for endpoint, count in (("source", 7), ("destination", 1)):
        inventory = snapshot["inventories"][endpoint]
        require(inventory["complete"] is True and inventory["wheat"] == count,
                "Completed endpoint inventory mismatch: " + endpoint)
    return snapshot
