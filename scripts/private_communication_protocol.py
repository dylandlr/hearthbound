#!/usr/bin/env python3
"""Predeclared, descriptive six-world private communication pilot.

The treatment is permission to send one-hop reports. Neither arm is required
to finish a task, and the communication arm is never required to outperform
the isolated arm. A fixed game-tick horizon is the scoring window.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from uuid import NAMESPACE_URL, uuid5

SCHEMA = "hearthbound.private-communication-trial-result.v1"
PLAN_SCHEMA = "hearthbound.private-communication-plan.v1"
RUNTIME_SCHEMA = "hearthbound.private-communication-trial.v1"
SUMMARY_SCHEMA = "hearthbound.private-communication-pilot.v1"
ARMS = ("NO_MESSAGES", "DIRECT")
SEEDS = (54101, 54102, 54103)
PLAN = tuple({"trial_id": f"pair-{i:02d}-{arm.lower().replace('_', '-')}",
              "pair_id": f"pair-{i:02d}", "seed": seed, "arm": arm,
              "policy_seed": seed}
             for i, seed in enumerate(SEEDS, 1) for arm in ARMS)
HORIZON_TICKS = 600
CADENCE_TICKS = 20
WALL_GUARD_SECONDS = 180
SOURCES = ((4, 101, 8), (4, 101, 4))
DESTINATION = (10, 101, 8)
INITIAL_STOCK = (2, 2)
POSITIONS = ((5.5, 101.0, 7.5), (12.5, 101.0, 7.5),
             (14.5, 101.0, 10.5), (12.5, 101.0, 12.5))
DIMENSION = "minecraft:overworld"
PROTOCOL_FILES = (
    "build.gradle", "settings.gradle", "gradle.properties",
    "gradle/forge-build-environment.gradle", "gradle/force-forge-tool-fallback.init.gradle",
    "scripts/run_forge_build_preflight.py",
    "scripts/private_communication_protocol.py",
    "scripts/rcon_private_communication_trial.py",
    "scripts/run_private_communication_trial.py",
    "scripts/summarize_private_communication_pilot.py",
    "scripts/test_private_communication_pilot.py",
    ".github/workflows/real-private-communication-pilot.yml",
    "src/main/java/dev/hearthbound/civilization/PrivateCommunicationPolicy.java",
    "src/main/java/dev/hearthbound/civilization/CommunicationNetworkPolicy.java",
    "src/main/java/dev/hearthbound/civilization/BoundedSourceDiscovery.java",
    "src/main/java/dev/hearthbound/civilization/CommunicationJournal.java",
    "src/main/java/dev/hearthbound/world/PrivateCommunicationTrial.java",
    "src/main/java/dev/hearthbound/world/CivilizationRuntime.java",
    "src/main/java/dev/hearthbound/world/CitizenKnowledgeExchange.java",
    "src/main/java/dev/hearthbound/world/CitizenSourceKnowledge.java",
    "src/main/java/dev/hearthbound/world/CitizenCommunicationRecords.java",
    "src/main/java/dev/hearthbound/world/SourceWheatObservation.java",
    "src/main/java/dev/hearthbound/world/SourceReportSession.java",
    "src/main/java/dev/hearthbound/world/SableController.java",
    "src/main/java/dev/hearthbound/world/SableHauling.java",
    "src/main/java/dev/hearthbound/world/HaulClaims.java",
    "scripts/run_colony_reliability_trial.py",  # bounded NBT reader only
    "scripts/rcon_two_citizen_haul_acceptance.py",  # RCON frame helpers only
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def protocol_hash(repo):
    return digest({name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
                   for name in PROTOCOL_FILES})


def planned_trial(trial_id):
    matches = [row for row in PLAN if row["trial_id"] == trial_id]
    if len(matches) != 1:
        raise ValueError("Trial is not in the predeclared six-world cohort")
    return dict(matches[0])


def actor_uuid(seed, slot):
    if seed not in SEEDS or slot not in range(4):
        raise ValueError("Actor is not in the predeclared cohort")
    return str(uuid5(NAMESPACE_URL, f"hearthbound/private-communication-v1/{seed}/{slot}"))


def matched_manifest(seed):
    """Only controlled initial conditions, never post-treatment measurements."""
    return {
        "schema": "hearthbound.private-communication-initial-manifest.v1",
        "scenario": "TWO_PRIVATE_SOURCES_FOUR_HOMOGENEOUS_WORKERS_V1",
        "dimension": DIMENSION, "world_seed": seed, "policy_seed": seed,
        "policy_id": "SCRIPTED_PRIVATE_NEAREST_V1",
        "horizon_ticks": HORIZON_TICKS, "cadence_ticks": CADENCE_TICKS,
        "destination": list(DESTINATION), "destination_wheat": 0,
        "sources": [{"position": list(position), "wheat": stock}
                    for position, stock in zip(SOURCES, INITIAL_STOCK)],
        "actors": [{"slot": slot, "citizen": actor_uuid(seed, slot),
                    "position": list(position), "rotation": [0.0, 0.0],
                    "no_ai": True, "initial_cargo_wheat": 0,
                    "initial_direct_sources": 0, "initial_reports": 0,
                    "initial_haul_jobs": 0}
                   for slot, position in enumerate(POSITIONS)],
        "per_idle_round_caps": {"near_positions": 75, "near_inspections": 4,
                                "outer_positions": 75, "outer_inspections": 4,
                                "selected_rechecks": 1, "assignment_attempts": 1},
        "per_actor_round_send_cap": 1,
        "common_evidence_observation_age_ticks": 200,
        "private_source_capacity": 16,
        "communication": {"kind": "ONE_HOP_OWN_DIRECT_OBSERVATION_ONLY",
                          "range_blocks": 12, "sender_observation_max_age_ticks": 40,
                          "delivered_report_ttl_ticks": 200},
        "global_colony_task_board_visible": False,
        "initial_game_rules": {"doMobSpawning": False, "doDaylightCycle": False,
                               "doWeatherCycle": False, "randomTickSpeed": 0},
        "initial_daytime": 6000, "initial_weather": "clear",
        "arena": {"min": [0, 100, 0], "max": [24, 104, 16],
                  "floor_y": 100, "roof_y": 104, "material": "minecraft:stone"},
        "cleared_sensor_envelope": {"min": [-16, 100, -16], "max": [40, 105, 32],
                                    "material": "minecraft:air", "volume": 16758},
        "forceload_block_rectangle": {"min": [-16, -16], "max": [47, 47]},
        "vanilla_entity_rng_matched": False,
        "full_world_state_identical": False,
    }


def plan_document(repo, trial_id):
    trial = planned_trial(trial_id)
    manifest = matched_manifest(trial["seed"])
    return {
        "schema": PLAN_SCHEMA, **trial,
        "source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "source_tree": subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True).strip(),
        "protocol_sha256": protocol_hash(repo),
        "matched_initial_manifest": manifest,
        "matched_initial_manifest_sha256": digest(manifest),
        "planned_worlds": len(PLAN), "planned_pairs": len(SEEDS),
        "behavioral_retries_allowed": 0,
        "primary_outcome": "DESTINATION_WHEAT_GAIN_AT_FIXED_GAME_TICK_HORIZON",
        "secondary_outcomes": {
            "first_delivery_relative_tick": "FIRST_VERIFIED_PHYSICAL_DELIVERY_OR_NULL",
            "all_four_delivery_relative_tick": "FOURTH_VERIFIED_DELIVERY_OR_NULL_CENSORED_AT_600",
            "output_ticks": "SUM_600_MINUS_VERIFIED_DELIVERY_RELATIVE_TICK_WHEAT_TICKS",
            "citizen_contributions": "PHYSICAL_DELIVERY_COUNTS_NO_FIXED_ROLE_OR_PARTICIPATION_QUOTA",
        },
        "wall_guard_seconds": WALL_GUARD_SECONDS,
        "inference_scope": "SMALL_DESCRIPTIVE_PAIRED_PILOT",
        "communication_win_required": False,
        "learned_collaboration": False, "reward_authorized": False,
    }


def write_plan(repo, trial_id, path):
    planned = plan_document(repo, trial_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(json.dumps(planned, indent=2, sort_keys=True) + "\n")
    return planned


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_plan(Path(__file__).resolve().parents[1], args.trial_id, args.output)
