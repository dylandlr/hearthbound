#!/usr/bin/env python3
"""Prospective six-world engineering qualification, separate from the 144-world study."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from uuid import NAMESPACE_URL, uuid5

from communication_preregistration import arm_definitions, load_document
from private_communication_protocol import (
    CADENCE_TICKS, DESTINATION, DIMENSION, HORIZON_TICKS, INITIAL_STOCK,
    POSITIONS as PHYSICAL_SEATS, PROTOCOL_FILES as LEGACY_PROTOCOL_FILES,
    SOURCES, WALL_GUARD_SECONDS, canonical, digest,
)

SCHEMA = "hearthbound.network-qualification-result.v1"
PLAN_SCHEMA = "hearthbound.network-qualification-plan.v1"
RUNTIME_SCHEMA = "hearthbound.communication-network-trial.v2"
SUMMARY_SCHEMA = "hearthbound.network-qualification-summary.v1"
LEDGER_SCHEMA = "hearthbound.network-qualification-evidence-digests.v1"
DESIGN_SHA256 = "43588a883e3c5674deff44e022ca9c4819d5e1ca48c82b664884ff603fdc6b45"
ARMS = ("NO_MESSAGES", "DIRECT", "DIRECT_UNREAD", "STAR", "CHAIN", "CYCLE")
WORLD_SEED = 56101
POLICY_SEED = 66104
BLOCK_ID = "qualification-01"
SLOT_TO_SEAT = (2, 0, 3, 1)
POSITIONS = tuple(PHYSICAL_SEATS[seat] for seat in SLOT_TO_SEAT)
PLAN = tuple({"trial_id": "qual-" + arm.lower().replace("_", "-"),
              "block_id": BLOCK_ID, "execution_index": index,
              "seed": WORLD_SEED, "policy_seed": POLICY_SEED, "arm": arm}
             for index, arm in enumerate(ARMS))
EDGES = {row["arm"]: row["undirected_permission_edges"] for row in arm_definitions()}
PROTOCOL_FILES = tuple(dict.fromkeys((*LEGACY_PROTOCOL_FILES,
    "scripts/network_qualification_protocol.py", "scripts/rcon_network_qualification.py",
    "scripts/run_network_qualification.py", "scripts/summarize_network_qualification.py",
    "scripts/network_qualification_native.py",
    "scripts/test_network_qualification.py", ".github/workflows/real-network-qualification.yml",
    "docs/experiments/communication-v1.design.json", "scripts/communication_preregistration.py",
    "src/main/java/dev/hearthbound/civilization/CommunicationNetworkPolicy.java")))
CAPABILITY_REQUIREMENTS = {
    "NO_MESSAGES": {"network_disabled_attempts_min": 1, "deliveries": 0, "policy_reads": 0},
    "DIRECT": {"deliveries_min": 1},
    "DIRECT_UNREAD": {"deliveries_min": 1, "policy_reads": 0, "selections": 0,
                      "report_cued_assignments": 0, "report_cued_completions": 0},
    "STAR": {"topology_blocked_attempts_min": 1, "allowed_transport_attempts_min": 1},
    "CHAIN": {"topology_blocked_attempts_min": 1, "allowed_transport_attempts_min": 1},
    "CYCLE": {"topology_blocked_attempts_min": 1, "allowed_transport_attempts_min": 1},
}


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON key: " + key)
        value[key] = item
    return value


def parse_json(text):
    def invalid(value):
        raise ValueError("Nonfinite JSON constant: " + value)
    return json.loads(text,
                      object_pairs_hook=_unique_object, parse_constant=invalid)


def load_json(path):
    return parse_json(Path(path).read_text(encoding="utf-8"))


def context():
    return {"workflow": os.environ.get("GITHUB_WORKFLOW"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
            "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}


def protocol_hash(repo):
    return digest({name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
                   for name in PROTOCOL_FILES})


def planned_trial(trial_id):
    matches = [row for row in PLAN if row["trial_id"] == trial_id]
    if len(matches) != 1:
        raise ValueError("Trial is not in the predeclared qualification cohort")
    return dict(matches[0])


def actor_uuid(seed, slot):
    if type(seed) is not int or seed != WORLD_SEED or type(slot) is not int or slot not in range(4):
        raise ValueError("Actor is not in the qualification cohort")
    return str(uuid5(NAMESPACE_URL, f"hearthbound/network-qualification-v1/{seed}/{slot}"))


def initial_manifest(seed):
    if seed != WORLD_SEED:
        raise ValueError("Qualification seed changed")
    return {
        "schema": "hearthbound.network-qualification-initial-manifest.v1",
        "scenario": "TWO_PRIVATE_SOURCES_FOUR_HOMOGENEOUS_WORKERS_V1",
        "dimension": DIMENSION, "world_seed": seed, "policy_seed": POLICY_SEED,
        "policy_id": "SCRIPTED_PRIVATE_NEAREST_V1", "design_sha256": DESIGN_SHA256,
        "qualification_only": True, "expanded_study_world": False,
        "slot_to_seat": list(SLOT_TO_SEAT), "physical_seat_positions": [list(p) for p in PHYSICAL_SEATS],
        "horizon_ticks": HORIZON_TICKS, "cadence_ticks": CADENCE_TICKS,
        "destination": list(DESTINATION), "destination_wheat": 0,
        "sources": [{"position": list(p), "wheat": n} for p, n in zip(SOURCES, INITIAL_STOCK)],
        "actors": [{"slot": slot, "physical_seat": SLOT_TO_SEAT[slot], "citizen": actor_uuid(seed, slot),
                    "position": list(position), "rotation": [0.0, 0.0], "no_ai": True,
                    "initial_cargo_wheat": 0, "initial_direct_sources": 0,
                    "initial_reports": 0, "initial_haul_jobs": 0}
                   for slot, position in enumerate(POSITIONS)],
        "per_idle_round_caps": {"near_positions": 75, "near_inspections": 4,
                                "outer_positions": 75, "outer_inspections": 4,
                                "selected_rechecks": 1, "assignment_attempts": 1},
        "per_actor_round_send_cap": 1, "communication_opportunities": 120,
        "common_evidence_observation_age_ticks": 200, "private_source_capacity": 16,
        "communication": {"kind": "ONE_HOP_OWN_DIRECT_OBSERVATION_ONLY", "range_blocks": 12,
                          "sender_observation_max_age_ticks": 40, "delivered_report_ttl_ticks": 200},
        "global_colony_task_board_visible": False,
        "initial_game_rules": {"doMobSpawning": False, "doDaylightCycle": False,
                               "doWeatherCycle": False, "randomTickSpeed": 0},
        "initial_daytime": 6000, "initial_weather": "clear",
        "arena": {"min": [0, 100, 0], "max": [24, 104, 16], "floor_y": 100,
                  "roof_y": 104, "material": "minecraft:stone"},
        "cleared_sensor_envelope": {"min": [-16, 100, -16], "max": [40, 105, 32],
                                    "material": "minecraft:air", "volume": 16758},
        "forceload_block_rectangle": {"min": [-16, -16], "max": [47, 47]},
        "vanilla_entity_rng_matched": False, "full_world_state_identical": False,
    }


def plan_document(repo, trial_id, declaration_utc=None, execution_context=None):
    design = load_document(repo / "docs/experiments/communication-v1.design.json")
    if design["design_sha256"] != DESIGN_SHA256:
        raise ValueError("Frozen expanded design changed")
    trial = planned_trial(trial_id)
    manifest = initial_manifest(trial["seed"])
    if declaration_utc is not None:
        stamp = datetime.fromisoformat(declaration_utc)
        if stamp.tzinfo is None or stamp.utcoffset().total_seconds() != 0:
            raise ValueError("Qualification declaration requires UTC timestamp")
    return {"schema": PLAN_SCHEMA, **trial, "declaration_utc": declaration_utc,
        "source_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "source_tree": subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True).strip(),
        "protocol_sha256": protocol_hash(repo), "execution_context": context() if execution_context is None else execution_context,
        "design_sha256": DESIGN_SHA256, "qualification_only": True, "expanded_study_worlds": 0,
        "initial_manifest": manifest, "initial_manifest_sha256": digest(manifest),
        "undirected_permission_edges": EDGES[trial["arm"]],
        "transport_enabled": trial["arm"] != "NO_MESSAGES",
        "reports_exposed_to_decisions": trial["arm"] not in ("NO_MESSAGES", "DIRECT_UNREAD"),
        "planned_worlds": 6, "world_attempts_allowed": 1, "build_attempts_allowed": 1,
        "max_concurrent_worlds": 2, "scheduling_order": "UNCONTROLLED_GITHUB_MATRIX",
        "automatic_retries_allowed": 0, "replacement_worlds_allowed": 0,
        "wall_guard_seconds": WALL_GUARD_SECONDS,
        "capability_requirements": CAPABILITY_REQUIREMENTS[trial["arm"]],
        "coverage_distinct_from_valid_observation": True, "coverage_absence_allows_replacement": False,
        "performance_win_required": False, "physical_completion_quota": None,
        "inference_scope": "ENGINEERING_CAPABILITY_QUALIFICATION_ONLY",
        "learned_collaboration": False, "llm_control": False, "reward_authorized": False,
        "expanded_study_execution_authorized": False}


def write_plan(repo, trial_id, path):
    planned = plan_document(repo, trial_id, datetime.now(timezone.utc).isoformat())
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(planned, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return planned


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-id", required=True, choices=[row["trial_id"] for row in PLAN])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_plan(Path(__file__).resolve().parents[1], args.trial_id, args.output)
