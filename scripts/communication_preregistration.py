#!/usr/bin/env python3
"""Freeze and validate an OFFLINE communication study; this is not a runner.

Only the exact versioned design is accepted. Even a valid document cannot be
executed by this module: the future runtime, capability evidence, and binding
format have not been implemented. No Minecraft, network, or subprocess imports.
"""
import argparse
from collections import Counter
import hashlib
import itertools
import json
from pathlib import Path
import sys
from uuid import NAMESPACE_URL, uuid5


SCHEMA = "hearthbound.communication-preregistration.v1"
DESIGN_ID = "COMMUNICATION_PERMISSION_GRAPHS_V1"
BASELINE_COMMIT = "31febdd08223b5575a09da14a51b3a036726ceb9"
ARMS = ("NO_MESSAGES", "DIRECT", "DIRECT_UNREAD", "STAR", "CHAIN", "CYCLE")
WORLD_SEEDS = tuple(range(55101, 55125))
POLICY_SEEDS = (65104, 65101, 65103, 65105, 65107, 65102,
                65109, 65106, 65108, 65110, 65112, 65111,
                65114, 65115, 65113, 65119, 65117, 65116,
                65123, 65120, 65118, 65124, 65122, 65121)
ORDER_OFFSETS = (0, 1, 3, 1, 3, 2)
PILOT_SEEDS = (54101, 54102, 54103)
POSITIONS = ((5.5, 101.0, 7.5), (12.5, 101.0, 7.5),
             (14.5, 101.0, 10.5), (12.5, 101.0, 12.5))
DEFAULT_MANIFEST = (Path(__file__).resolve().parents[1]
                    / "docs/experiments/communication-v1.design.json")


class ExecutionBlocked(ValueError):
    """A design document never grants permission or capabilities to run."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def arm_definitions():
    """Undirected allowed edges, represented once as sorted logical-slot pairs."""
    complete = [list(edge) for edge in itertools.combinations(range(4), 2)]
    edges = {
        "NO_MESSAGES": [], "DIRECT": complete, "DIRECT_UNREAD": complete,
        "STAR": [[0, 1], [0, 2], [0, 3]],
        "CHAIN": [[0, 1], [1, 2], [2, 3]],
        "CYCLE": [[0, 1], [0, 3], [1, 2], [2, 3]],
    }
    return [{"arm": arm, "undirected_permission_edges": edges[arm],
             "transport_enabled": arm != "NO_MESSAGES",
             "reports_exposed_to_decisions": arm not in ("NO_MESSAGES", "DIRECT_UNREAD"),
             "baseline_arm_supported": arm in ("NO_MESSAGES", "DIRECT"),
             "expanded_runtime_qualified": False}
            for arm in ARMS]


def schedule():
    """Every seat permutation once; cyclic Latin orders, with no RNG dependency."""
    blocks, worlds = [], []
    for index, permutation in enumerate(itertools.permutations(range(4))):
        block_id = f"block-{index + 1:02d}"
        offset = index % len(ARMS)
        order = ARMS[offset:] + ARMS[:offset]
        seed, policy_seed = WORLD_SEEDS[index], POLICY_SEEDS[index]
        blocks.append({
            "block_id": block_id, "world_seed": seed, "policy_seed": policy_seed,
            "slot_to_physical_seat": list(permutation), "arm_order": list(order),
            "actors": [{
                "logical_slot": slot, "physical_seat": seat,
                "citizen": str(uuid5(NAMESPACE_URL,
                    f"hearthbound/communication-preregistration-v1/{seed}/{slot}")),
                "initial_position": list(POSITIONS[seat]),
            } for slot, seat in enumerate(permutation)],
        })
        for position, arm in enumerate(order, 1):
            worlds.append({
                "execution_index": len(worlds) + 1,
                "trial_id": f"comm-v1-{block_id}-{arm.lower().replace('_', '-')}",
                "block_id": block_id, "world_seed": seed, "policy_seed": policy_seed,
                "arm": arm, "position_within_block": position,
            })
    return blocks, worlds


def design_body():
    blocks, worlds = schedule()
    return {
        "design_id": DESIGN_ID,
        "status": "OFFLINE_PREREGISTRATION_NOT_RUNTIME_READY",
        "execution_allowed": False,
        "baseline_inspected_commit": BASELINE_COMMIT,
        "baseline_is_execution_binding": False,
        "runtime_binding": None,
        "study_question": "Effect of bounded information exchange and permission graphs on physical output",
        "inference_scope": "PRESPECIFIED_SCRIPTED_FOUR_WORKER_FIXTURE",
        "learning_updates": 0, "llm_calls": 0,
        "societal_emergence_claim_authorized": False,
        "reward_or_policy_promotion_authorized": False,
        "pilot_separate": {"world_seeds": list(PILOT_SEEDS), "pool_with_new_study": False,
                           "planned_worlds": 6, "valid_worlds": 5, "complete_pairs": 2,
                           "complete_pair_output_deltas": [1, 0],
                           "pre_runtime_setup_failures": 1},
        "sample": {"planned_worlds": 144, "planned_seed_blocks": 24,
                   "worlds_per_arm": 24, "citizens_per_world": 4,
                   "statistical_unit": "FRESH_WORLD",
                   "paired_resampling_unit": "SEED_BLOCK",
                   "size_reason": "ALL_24_SEAT_PERMUTATIONS_AND_BALANCED_SIX_ARM_ORDER",
                   "power_analysis_performed": False,
                   "independence_requires": "NEW_WORLD_SESSION_JVM_AND_EMPTY_AGENT_STATE_PER_TRIAL"},
        "counterbalancing": {
            "seat_permutations": "LEXICOGRAPHIC_ALL_24_PERMUTATIONS_OF_0_1_2_3",
            "arm_order": "ROTATE_BASE_ORDER_LEFT_BY_ZERO_BASED_BLOCK_INDEX_MODULO_6",
            "policy_order_offsets": list(ORDER_OFFSETS),
            "first_logical_slot": "((block_index // 6) + offsets[block_index % 6]) % 4",
            "policy_seed_assignment": "LOWEST_UNUSED_SEED_IN_65101_TO_65124_WITH_REQUIRED_REMAINDER_MODULO_4",
            "offset_selection": "LEXICOGRAPHIC_FIRST_SIX_OFFSETS_BALANCING_ALL_FOUR_PHYSICAL_ROUND_PHASES",
            "physical_seat_first_counts_per_round_phase": [6, 6, 6, 6],
            "physical_seat_first_counts_over_30_rounds": [180, 180, 180, 180],
            "outcome_data_used": False,
        },
        "arms": arm_definitions(),
        "fixture": {
            "scenario": "TWO_PRIVATE_SOURCES_FOUR_HOMOGENEOUS_WORKERS_V1",
            "dimension": "minecraft:overworld", "policy_id": "SCRIPTED_PRIVATE_NEAREST_V1",
            "destination": [10, 101, 8], "destination_wheat": 0,
            "sources": [{"position": [4, 101, 8], "wheat": 2},
                        {"position": [4, 101, 4], "wheat": 2}],
            "physical_seat_positions": [list(position) for position in POSITIONS],
            "actor_initial_state": {"rotation": [0.0, 0.0], "no_ai": True,
                                    "cargo_wheat": 0, "direct_sources": 0,
                                    "inbox_reports": 0, "haul_jobs": 0},
            "global_colony_task_board_visible": False,
            "shared_claims": "EXCLUSION_ONLY_FOR_ALREADY_PRIVATELY_KNOWN_SOURCES",
            "initial_game_rules": {"doMobSpawning": False, "doDaylightCycle": False,
                                   "doWeatherCycle": False, "randomTickSpeed": 0},
            "initial_daytime": 6000, "initial_weather": "clear",
            "arena": {"min": [0, 100, 0], "max": [24, 104, 16],
                      "floor_y": 100, "roof_y": 104, "material": "minecraft:stone"},
            "cleared_sensor_envelope": {"min": [-16, 100, -16], "max": [40, 105, 32],
                                        "material": "minecraft:air", "volume": 16758},
            "forceload_block_rectangle": {"min": [-16, -16], "max": [47, 47]},
            "vanilla_entity_rng_matched": False, "full_world_state_identical": False,
        },
        "timing": {"horizon_game_ticks": 600, "round_cadence_game_ticks": 20,
                   "relative_round_ticks": list(range(0, 600, 20)),
                   "horizon_wall_guard_seconds": 180,
                   "decision_window": "0_LE_RELATIVE_TICK_LT_600",
                   "freeze_at_relative_tick": 600,
                   "witness_capture": "AFTER_FREEZE_WITH_VERIFIED_NO_POST_HORIZON_STATE_CHANGE",
                   "witness_capture_tick_may_exceed_horizon": True,
                   "delivery_window": "0_LE_VERIFIED_DELIVERY_RELATIVE_TICK_LT_600",
                   "completed_world_early_stop": False,
                   "phase_order": ["MOTOR", "IDLE_DISCOVERY", "COMMUNICATION", "IDLE_DECISION"],
                   "first_slot_formula": "((policy_seed % 4) + (round % 4)) % 4",
                   "slot_order": "FIRST_THEN_NEXT_THREE_MODULO_FOUR"},
        "budgets": {
            "per_idle_actor_round": {"near_positions": 75, "near_inspections": 4,
                                     "outer_positions": 75, "outer_inspections": 4,
                                     "selected_rechecks": 1, "assignment_attempts": 1},
            "per_actor_round_send_attempts": 1,
            "max_send_attempts_per_world": 120,
            "sensor_radius_blocks": 16,
            "direct_source_capacity": 16, "inbox_capacity": 16, "decision_source_capacity": 16,
            "evidence_max_age_from_observation_ticks": 200,
            "runtime_record_capacity": 4096, "message_history_capacity": 1024,
            "message_event_capacity": 8192, "send_history_capacity": 2048,
            "overflow_or_recording_error": "INVALID_PROTOCOL_RETAIN_WORLD_NO_TRUNCATION_AS_VALID",
            "unused_budget_transfer": False,
            "realized_computation_equalized": False,
        },
        "transport": {
            "payload": "SENDER_OWN_DIRECT_OBSERVATION_ONLY",
            "payload_source_order": "X_THEN_Y_THEN_Z_ASCENDING",
            "payload_choice": "FRESH_OWN_OBSERVATIONS[round % count]",
            "fresh_sender_observation_max_age_ticks": 40,
            "recipient_proposal": "(sender_slot + 1 + (round % 3)) % 4",
            "proposal_uses_unchanged_all_peer_rotation": True,
            "graph_labels_are_logical_slots": True,
            "undirected_edge_allows_both_directions": True,
            "edge_policy_is_fixed_for_whole_world": True,
            "send_charge_point": "BEFORE_NETWORK_EDGE_RANGE_AND_DUPLICATE_CHECKS",
            "no_fresh_own_payload": "NO_SEND_ATTEMPT_RECORD_OPPORTUNITY_AS_NO_ELIGIBLE_PAYLOAD",
            "denial_precedence": ["NETWORK_DISABLED", "TOPOLOGY_BLOCKED", "EXISTING_TRANSPORT_CHECKS"],
            "denied_attempt_consumes_budget": True,
            "retry_another_recipient_same_round": False,
            "range_blocks": 12, "same_dimension_required": True,
            "delivery": "EXISTING_SYNCHRONOUS_RECIPIENT_PRIVATE_INBOX",
            "delivery_ttl_ticks": 200,
            "duplicate_key": "SENDER_SOURCE_REVISION_OBSERVED_TICK_WORLD_EPISODE_RECIPIENT",
            "duplicate_refreshes_delivery_or_evidence_age": False,
            "inbox_admission": "PRUNE_EXPIRED_THEN_FIFO_EVICT_TO_16_RETAIN_AUDIT_HISTORY",
            "max_route_hops": 1, "relaying": False,
            "route": "[actual_sender_uuid, actual_recipient_uuid]",
            "guaranteed_realized_connectivity": False,
            "degree_or_permitted_message_volume_matched": False,
            "graph_structure_effect_isolated_from_cost": False,
            "direct_unread": "NORMAL_TRUTHFUL_DELIVERY_NO_POLICY_READ_NO_SELECTED_NO_REPORT_CUED_ASSIGNMENT",
            "reports_change_direct_memory_by_delivery": False,
            "selection_requires_own_fresh_positive_recheck": True,
        },
        "required_evidence": {
            "identity": ["trial_id", "block_id", "source_commit", "protocol_sha256",
                         "world_uuid", "episode_uuid", "citizen_uuid", "logical_slot", "physical_seat"],
            "send": ["attempt_id", "tick", "round", "sender", "recipient", "source",
                     "original_observed_tick", "source_revision", "permission_edge",
                     "edge_permitted", "route", "budget_charge", "outcome", "reason"],
            "delivery": ["message_id", "attempt_id", "report_id", "sender", "recipient",
                         "source", "reported_state", "reported_wheat", "original_observed_tick",
                         "source_revision", "sent_tick", "delivered_tick", "expires_after_tick",
                         "world_uuid", "episode_uuid"],
            "separate_lifecycle_events": ["SEND_ATTEMPT", "REJECTED", "DUPLICATE", "DELIVERED",
                                          "READ", "SELECTED", "RECHECK", "ASSIGNED", "PHYSICAL_COMPLETED"],
            "decision_and_physical_binding": ["decision_id", "report_id_or_null", "direct_recheck",
                                              "job_id", "citizen_uuid", "source", "destination",
                                              "assigned_tick", "completed_tick", "wheat_transferred"],
            "retained_message_classifications": ["NEVER_READ", "NEVER_SELECTED", "EXPIRED_AT_HORIZON",
                                                  "SUPERSEDED", "INBOX_EVICTED"],
            "classifications_may_overlap": True,
            "independent_witnesses": ["initial_and_horizon_source_inventory", "initial_and_horizon_destination_inventory",
                                      "all_enrolled_citizen_cargo_and_native_job_tags", "native_level_dat_seed",
                                      "saved_world_identity_and_communication_journal"],
            "artifact_digests": ["preflight_plan", "runtime_binding", "server_log", "rcon_log", "result_json",
                                 "level_dat", "saved_world_data", "native_actor_export", "scorer_replay"],
            "operator_audit_is_policy_consumption": False,
            "message_chain_establishes_counterfactual_benefit": False,
        },
        "cost_accounting": {
            "report_per_world_and_per_citizen": ["controller_rounds", "idle_opportunities", "motor_ticks",
                "near_positions", "near_inspections", "outer_positions", "outer_inspections", "rechecks",
                "assignment_attempts", "accepted_assignments", "completed_jobs", "send_opportunities",
                "no_eligible_payload_opportunities", "send_attempts", "network_disabled", "topology_blocked",
                "transport_rejections_by_reason", "duplicates", "delivered_messages", "report_reads",
                "report_selections", "report_cued_assignments", "report_cued_physical_completions",
                "expired_reports", "inbox_evictions", "capacity_denials", "recording_errors",
                "motor_elapsed_ns", "discovery_elapsed_ns", "communication_elapsed_ns", "decision_elapsed_ns"],
            "aggregate_costs": "SUM_WORLD_TOTALS_WITH_VALID_AND_PLANNED_WORLD_DENOMINATORS",
            "time_scope": "ADAPTER_ONLY_NOT_TOTAL_SERVER_CPU_OR_MATCHED_HARDWARE",
            "zero_cost_efficiency_ratio": None,
            "costs_award_physical_or_research_reward": False,
        },
        "outcomes": {
            "primary": "INDEPENDENT_DESTINATION_WHEAT_GAIN_AT_TICK_600",
            "primary_range": [0, 4],
            "primary_contrast": {"treatment": "DIRECT", "reference": "NO_MESSAGES"},
            "secondary_contrasts": [
                {"treatment": "DIRECT", "reference": "DIRECT_UNREAD"},
                {"treatment": "STAR", "reference": "DIRECT"},
                {"treatment": "CHAIN", "reference": "DIRECT"},
                {"treatment": "CYCLE", "reference": "DIRECT"}],
            "secondary": {
                "output_ticks": "SUM_FOR_VERIFIED_DELIVERIES_OF_WHEAT_TIMES_600_MINUS_RELATIVE_TICK",
                "output_ticks_range": [0, 2400],
                "first_delivery_tick": "VERIFIED_FIRST_DELIVERY_OR_NULL_WITH_CENSOR_AT_600",
                "fourth_delivery_tick": "VERIFIED_FOURTH_DELIVERY_OR_NULL_WITH_CENSOR_AT_600",
                "timing_difference": "NULL_IF_EITHER_MEMBER_CENSORED_OR_MISSING",
                "physical_contributions": "PER_CITIZEN_VERIFIED_DELIVERIES_NO_PARTICIPATION_QUOTA",
                "remaining_work": "SOURCE_STOCK_CARGO_ACTIVE_JOBS_CLAIMS_AT_HORIZON",
                "communication_mechanisms_and_costs": "REQUIRED_EVIDENCE_AND_COST_ACCOUNTING"},
            "complete_output_required_for_validity": False,
            "communication_win_required": False,
            "four_wheat_ceiling_acknowledged": True,
            "primary_endpoint_switching_allowed": False,
        },
        "analysis": {
            "per_world_rows": "ALL_144_PLANNED_WORLDS_WITH_NULL_UNOBSERVED_OUTCOMES",
            "complete_block_requirement_for_each_contrast": "ONLY_THE_TWO_NAMED_ARMS_MUST_BE_VALID",
            "report": ["PLANNED_VALID_INVALID_NOT_RUN_COUNTS_BY_ARM", "ALL_PAIRED_WORLD_VALUES_AND_DELTAS",
                       "MEAN_AND_MEDIAN_COMPLETE_PAIR_DELTA", "POSITIVE_ZERO_NEGATIVE_PAIR_COUNTS",
                       "COMPLETE_PAIR_BOOTSTRAP_INTERVAL", "ALL_24_BLOCK_MISSINGNESS_BOUNDS"],
            "bootstrap": {"outcome": "PRIMARY_DESTINATION_WHEAT_GAIN_ONLY",
                          "replicates": 10000, "seed": 76124, "unit": "COMPLETE_SEED_BLOCK",
                          "implementation": "PYTHON_RANDOM_RANDOM_FLOOR_TIMES_N_WITH_REPLACEMENT",
                          "contrast_order": "PRIMARY_THEN_SECONDARY_AS_LISTED_RESET_RNG_PER_CONTRAST",
                          "interval": "SORTED_REPLICATE_MEANS_ZERO_BASED_INDICES_249_AND_9749",
                          "minimum_complete_pairs": 2,
                          "interpretation": "DESCRIPTIVE_CONDITIONAL_ON_VALID_PAIRS_NOT_SELECTION_BIAS_REPAIR"},
            "missingness_bounds": {
                "observed_primary_interval": "[y,y]",
                "unobserved_or_invalid_primary_interval": "[0,4]",
                "block_contrast_interval": "[treatment_low-reference_high,treatment_high-reference_low]",
                "planned_mean_interval": "SUM_24_BLOCK_LOWER_AND_UPPER_ENDPOINTS_DIVIDED_BY_24",
                "output_ticks_missing_interval": "[0,2400]",
                "assumes": "DECLARED_PHYSICAL_TARGET_RANGE_NOT_OBSERVED_INVALID_OUTPUT"},
            "hypothesis_tests_or_winner_thresholds": None,
            "topology_ranking_confirmed": False,
            "extra_contrasts": "EXPLORATORY_AND_LABELLED_AFTER_FIXED_PRIMARY_REPORT",
            "citizens_messages_or_rounds_are_independent_replicates": False,
            "historical_cohorts_pooled": False,
        },
        "missingness_and_stopping": {
            "statuses": ["VALID_OBSERVATION", "NOT_RUN_SETUP_FAILURE", "INVALID_PROTOCOL",
                         "INCOMPLETE_RUNTIME", "MISSING_ARTIFACTS", "NOT_RUN_COHORT_STOP"],
            "valid_zero_or_unfinished_output": "VALID_IF_FIXED_HORIZON_AND_EVIDENCE_CONTRACT_HOLD",
            "setup_failure_is_zero_output": False,
            "missing_world_replacement": False, "behavioral_retries": 0,
            "study_schedule": "SERIAL_EXECUTION_INDEX_ONE_WORLD_ATTEMPT_PER_SLOT_CONTINUE_AFTER_ISOLATED_FAILURE",
            "pre_world_dependency_setup_attempts": 1,
            "automatic_dependency_retries": 0,
            "dependency_failure": "RETAIN_FIRST_FAILURE_AS_UNKNOWN_NO_REPLACEMENT_SOURCE_OR_CONFIG_FIX_REQUIRES_NEW_COHORT",
            "dependency_attempt_logs_retained": True,
            "predeclare_plan_before_dependency_setup": True,
            "late_recovery_after_600_scored": False,
            "ordinary_stop": "AFTER_144_PLANNED_SLOTS_REGARDLESS_OF_RESULTS",
            "early_stop": "ONLY_INFRASTRUCTURE_UNAVAILABLE_OR_PROTOCOL_BREACH_REQUIRING_REVISION",
            "early_stop_records": "PRESERVE_ALL_ATTEMPTS_MARK_REMAINING_NOT_RUN_COHORT_STOP",
            "amendment": "NEW_VERSION_AND_COHORT_NO_SILENT_REPLACEMENT_OR_POOLING",
            "results_used_to_add_worlds_or_select_seeds": False,
        },
        "execution_gate": {
            "this_module_can_execute": False,
            "future_separate_binding_required": True,
            "required_frozen_hashes": ["design_sha256", "runtime_commit_and_tree", "runtime_protocol",
                                       "scorer_sources", "built_artifact", "resolved_dependencies",
                                       "workflow_and_launch_configuration"],
            "required_capabilities": ["ALL_SIX_RUNTIME_ARMS", "AUDITED_PERMISSION_EDGE_FILTER",
                "TRUTHFUL_DELIVERY_WITHOUT_DECISION_EXPOSURE", "EXACT_SEAT_AND_SEED_ENROLLMENT",
                "BOUNDED_OBSERVATION_AND_SEND_ACCOUNTING", "NO_RELAY_PRIVATE_OBSERVATION_BOUNDARY",
                "COMPLETE_LIFECYCLE_AND_UNUSED_REPORT_RECORDS", "EXACT_HORIZON_FREEZE_AND_NATIVE_WITNESSES",
                "FRESH_WORLD_SESSION_AND_JVM", "ALL_PLANNED_WORLD_DENOMINATORS",
                "INDEPENDENT_SCORER_REPLAY", "EXISTING_MINECRAFT_COMPATIBILITY_GATES"],
            "capability_evidence": "HASHED_ACCEPTANCE_ARTIFACTS_AT_EXACT_BOUND_REVISION_NOT_SELF_ATTESTED_FLAGS",
            "qualification_worlds_count_toward_144": False,
            "qualification_seeds_overlap_evaluation": False,
            "qualification_records_retained": True,
            "binding_may_change_arms_seeds_budgets_or_endpoints": False,
        },
        "references": {
            "foundation": "docs/PROJECT_SID_PA4_RESEARCH_FOUNDATION.md",
            "implementation_contract": "docs/PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md",
            "primary": ["PROJECT_SID_ARXIV_2411.00114V1", "MULTIAGENTBENCH_ACL_2025_LONG_421",
                        "MARBLE_OFFICIAL_IMPLEMENTATION_SAME_RESEARCH_EFFORT"],
            "pa4_mechanism_and_evaluation": ["P06", "P07", "P11", "P28", "P30", "P34", "P37", "P42"],
            "pa4_future_strategy_and_payoff_scope": ["P04", "P15", "P19", "P32", "P33"],
        },
        "blocks": blocks, "planned_worlds": worlds,
    }


def document():
    body = design_body()
    return {"schema": SCHEMA, "design_sha256": digest(body), "design": body}


def validate_document(value):
    """Strict closed schema: no extra fields, overrides, hashes, or trial rows."""
    if not isinstance(value, dict) or set(value) != {"schema", "design_sha256", "design"}:
        raise ValueError("Expected the exact preregistration envelope")
    if value["schema"] != SCHEMA:
        raise ValueError("Unknown preregistration schema")
    if not isinstance(value["design"], dict) or value["design_sha256"] != digest(value["design"]):
        raise ValueError("Design digest mismatch")
    if canonical(value["design"]) != canonical(design_body()):
        raise ValueError("Document differs from the frozen v1 design; a new version is required")
    # Independent balance checks guard against accidentally changing the builder.
    body = value["design"]
    blocks, worlds = body["blocks"], body["planned_worlds"]
    if len(blocks) != 24 or len(worlds) != 144:
        raise ValueError("Wrong planned-world denominator")
    if set(WORLD_SEEDS) & set(PILOT_SEEDS) or set(WORLD_SEEDS) & set(POLICY_SEEDS):
        raise ValueError("Seed ranges overlap")
    if len({tuple(row["slot_to_physical_seat"]) for row in blocks}) != 24:
        raise ValueError("Seat permutations are not complete")
    if Counter(row["arm"] for row in worlds) != Counter({arm: 24 for arm in ARMS}):
        raise ValueError("Arm counts are not balanced")
    for slot in range(4):
        if Counter(row["slot_to_physical_seat"][slot] for row in blocks) != Counter({i: 6 for i in range(4)}):
            raise ValueError("Topology role positions are not balanced")
    for arm in ARMS:
        if Counter(row["position_within_block"] for row in worlds if row["arm"] == arm) != Counter({i: 4 for i in range(1, 7)}):
            raise ValueError("Treatment order is not balanced")
    if Counter(row["policy_seed"] % 4 for row in blocks) != Counter({i: 6 for i in range(4)}):
        raise ValueError("First logical slot is not balanced")
    for phase in range(4):
        if Counter(row["slot_to_physical_seat"][(row["policy_seed"] + phase) % 4]
                   for row in blocks) != Counter({i: 6 for i in range(4)}):
            raise ValueError("Physical priority is not balanced at each round phase")
    return value["design_sha256"]


def require_executable(value):
    validate_document(value)
    raise ExecutionBlocked("OFFLINE DESIGN ONLY: no qualified expanded runtime or separate revision binding; execution is blocked")


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError(f"Nonfinite JSON constant: {value}")


def load_document(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"),
                       object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    validate_document(value)
    return value


def write_document(path):
    value = document()
    validate_document(value)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("write", "validate", "check-executable"))
    parser.add_argument("path", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)
    try:
        value = write_document(args.path) if args.command == "write" else load_document(args.path)
        if args.command == "check-executable":
            require_executable(value)
        print(json.dumps({"design_sha256": value["design_sha256"], "planned_worlds": 144,
                          "design_valid": True, "execution_allowed": False}, sort_keys=True))
        return 0
    except (OSError, ValueError, TypeError) as failure:
        print(str(failure), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
