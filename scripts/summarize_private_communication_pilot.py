#!/usr/bin/env python3
"""Validate artifacts and describe every planned world/pair without selecting winners."""
import argparse
import hashlib
import json
from pathlib import Path

from private_communication_protocol import (
    PLAN, PLAN_SCHEMA, SCHEMA, SEEDS, SUMMARY_SCHEMA, digest, matched_manifest,
    plan_document, protocol_hash,
)
from rcon_private_communication_trial import require, uuid, validate_trial


def verify_ledger(directory):
    ledger = json.loads((directory / "evidence-sha256.json").read_text())
    require(ledger["schema"] == "hearthbound.private-communication-evidence-digests.v1",
            "Invalid evidence digest schema")
    required = {"planned-trial.json", "trial-result.json", "forge-server.log", "rcon.log",
                "world-metadata/level.dat", "world-metadata/hearthbound_world_identity_v1.dat"}
    require(required <= set(ledger["files"]), "Required evidence missing from digest ledger")
    for name, expected in ledger["files"].items():
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe evidence path")
        path = directory / relative
        require(path.is_file() and not path.is_symlink(), "Missing or linked evidence file")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == expected, "Evidence digest mismatch: " + name)
    return len(ledger["files"])


def validate_result(result, plan, directory, repo, expected_commit):
    require(result["schema"] == SCHEMA and result["status"] == "VALID_OBSERVATION"
            and result["protocol_valid"] is True, "Trial did not finish with a valid observation")
    require(result["source_commit"] == expected_commit
            and result["protocol_sha256"] == protocol_hash(repo), "Mixed code revision or protocol")
    for key in ("trial_id", "pair_id", "seed", "arm", "policy_seed"):
        require(result[key] == plan[key], "Trial differs from predeclared cohort: " + key)
    require(result["behavioral_retries"] == 0 and result["fresh_world_directory"] is True
            and result["planned_worlds"] == 6 and result["planned_pairs"] == 3
            and result["clean_server_exit"] is True and result["phase"] == "FINISHED"
            and result["communication_win_required"] is False
            and result["causal_benefit_established"] is False
            and result["learned_collaboration"] is False and result["reward_authorized"] is False,
            "Trial execution or inference contract changed")
    planned = json.loads((directory / "planned-trial.json").read_text())
    expected_plan = plan_document(repo, plan["trial_id"])
    require(planned["schema"] == PLAN_SCHEMA and planned == expected_plan,
            "Predeclared manifest differs from checked-out protocol")
    require(result["source_tree"] == planned["source_tree"]
            and result["matched_initial_manifest_sha256"] == planned["matched_initial_manifest_sha256"]
            == digest(matched_manifest(plan["seed"])), "Initial-condition or source-tree hash mismatch")
    verified_files = verify_ledger(directory)
    metadata = directory / "world-metadata"
    # world_evidence expects the native SavedData layout. Read the same files
    # without copying or modifying downloaded evidence.
    from run_colony_reliability_trial import NbtReader
    import gzip
    level_bytes = (metadata / "level.dat").read_bytes()
    identity_bytes = (metadata / "hearthbound_world_identity_v1.dat").read_bytes()
    saved_level = NbtReader(gzip.decompress(level_bytes)).root()
    saved_identity = NbtReader(gzip.decompress(identity_bytes)).root()
    world = result["world"]
    require(world["generated_seed"] == plan["seed"] == saved_level["Data"]["WorldGenSettings"]["seed"]
            and world["configured_seed"] == str(plan["seed"]), "Saved world seed mismatch")
    require(world["world_uuid"] == uuid(saved_identity["data"]["worldUuid"])
            == result["fixture"]["final"]["world"], "Saved/runtime world identity mismatch")
    require(world["level_dat_sha256"] == hashlib.sha256(level_bytes).hexdigest()
            and world["world_identity_sha256"] == hashlib.sha256(identity_bytes).hexdigest(),
            "Saved metadata digest mismatch")
    require(world["level_name"] == "private-communication-" + plan["trial_id"]
            and world["origin"] == "PERSISTED_FORGE_LEVEL_DAT_AND_HEARTHBOUND_SAVEDDATA",
            "World origin mismatch")
    for name, filename in (("server_log_sha256", "forge-server.log"), ("rcon_log_sha256", "rcon.log")):
        require(result[name] == hashlib.sha256((directory / filename).read_bytes()).hexdigest(),
                "Log digest mismatch")
    metrics = validate_trial(result["fixture"], plan["seed"], plan["arm"])
    require(result["fixture"]["metrics"] == metrics, "Recorded score differs from artifact replay")
    return metrics, verified_files


def paired_summary(rows):
    """Retain six rows and three pairs; inference uses worlds, never citizens."""
    require(len(rows) == len(PLAN)
            and {row["trial_id"] for row in rows} == {row["trial_id"] for row in PLAN},
            "Summary denominator changed")
    by_id = {row["trial_id"]: row for row in rows}
    pairs = []
    for index, seed in enumerate(SEEDS, 1):
        pair_id = f"pair-{index:02d}"
        isolated = by_id[pair_id + "-no-messages"]
        direct = by_id[pair_id + "-direct"]
        pair = {"pair_id": pair_id, "seed": seed,
                "isolated_trial": isolated["trial_id"], "direct_trial": direct["trial_id"],
                "isolated_status": isolated["status"], "direct_status": direct["status"],
                "status": "INCOMPLETE_OR_INVALID_PAIR", "delta_direct_minus_isolated": None}
        if isolated["status"] == direct["status"] == "VALID_OBSERVATION":
            left, right = isolated["metrics"], direct["metrics"]
            require(isolated["matched_initial_manifest_sha256"] == direct["matched_initial_manifest_sha256"],
                    "Paired initial manifests differ")
            require(isolated["world_uuid"] != direct["world_uuid"] and isolated["episode"] != direct["episode"],
                    "Paired worlds/sessions were not independent")
            pair["status"] = "VALID_PAIRED_OBSERVATION"
            delta = {"physical_wheat_delivered": right["physical_wheat_delivered"] - left["physical_wheat_delivered"],
                     "output_ticks": right["output_ticks"] - left["output_ticks"],
                     "first_delivery_relative_tick": None, "all_four_delivery_relative_tick": None,
                     "costs": {name: right["costs"][name] - left["costs"][name]
                               for name in left["costs"]}}
            for name in ("first_delivery_relative_tick", "all_four_delivery_relative_tick"):
                if left[name] is not None and right[name] is not None:
                    delta[name] = right[name] - left[name]
            pair["delta_direct_minus_isolated"] = delta
            pair["isolated_primary_outcome"] = left["physical_wheat_delivered"]
            pair["direct_primary_outcome"] = right["physical_wheat_delivered"]
            pair["first_delivery_delta_missing_if_either_censored"] = True
            pair["all_four_delta_missing_if_either_censored"] = True
        pairs.append(pair)
    valid = [row for row in rows if row["status"] == "VALID_OBSERVATION"]
    valid_pairs = [row for row in pairs if row["status"] == "VALID_PAIRED_OBSERVATION"]
    deltas = [row["delta_direct_minus_isolated"]["physical_wheat_delivered"] for row in valid_pairs]
    mechanism = {
        "isolated_direct_only_delivery_exercised": any(row["arm"] == "NO_MESSAGES"
            and row["metrics"]["direct_only_physical_jobs"] > 0 for row in valid),
        "complete_report_cued_delivery_chain_exercised": any(row["arm"] == "DIRECT"
            and row["metrics"]["communication"]["report_cued_physical_jobs"] > 0 for row in valid),
        "coverage_is_separate_from_trial_validity": True,
        "absence_of_coverage_is_retained_as_a_null_mechanism_result": True,
    }
    return {"schema": SUMMARY_SCHEMA, "planned_worlds": len(PLAN), "planned_pairs": len(SEEDS),
            "valid_world_observations": len(valid), "invalid_or_missing_worlds": len(PLAN) - len(valid),
            "valid_paired_observations": len(valid_pairs), "invalid_or_incomplete_pairs": len(SEEDS) - len(valid_pairs),
            "worlds": rows, "pairs": pairs, "mechanism_coverage": mechanism,
            "primary_paired_deltas": deltas,
            "mean_primary_paired_delta": sum(deltas) / len(deltas) if deltas else None,
            "direct_higher_pairs": sum(value > 0 for value in deltas),
            "equal_output_pairs": sum(value == 0 for value in deltas),
            "direct_lower_pairs": sum(value < 0 for value in deltas),
            "comparison_unit": "INDEPENDENT_WORLD_PAIRED_BY_PREDECLARED_SEED_AND_INITIAL_MANIFEST",
            "primary_outcome": "DESTINATION_WHEAT_GAIN_AT_FIXED_GAME_TICK_HORIZON",
            "performance_win_required": False, "inference_scope": "SMALL_DESCRIPTIVE_PAIRED_PILOT",
            "causal_benefit_established": False, "learned_collaboration": False,
            "original_four_citizen_reliability_cohort": False,
            "vanilla_entity_rng_matched": False, "full_world_state_identical": False,
            "uncertainty": "THREE_PLANNED_PAIRS; NO_POPULATION_EFFECT_OR_TOPOLOGY_WINNER_INFERENCE"}


def summarize(root, repo, expected_commit):
    rows, unexpected = [], []
    results, plans = {}, {}
    for path in sorted(root.rglob("trial-result.json")) if root.exists() else []:
        try:
            value = json.loads(path.read_text())
            results.setdefault(value["trial_id"], []).append((path, value))
        except Exception as error:
            unexpected.append({"path": str(path.relative_to(root)), "error": type(error).__name__ + ": " + str(error)})
    for path in sorted(root.rglob("planned-trial.json")) if root.exists() else []:
        try:
            value = json.loads(path.read_text())
            plans.setdefault(value["trial_id"], []).append(path)
        except Exception as error:
            unexpected.append({"path": str(path.relative_to(root)), "error": type(error).__name__ + ": " + str(error)})
    known = {row["trial_id"] for row in PLAN}
    for trial_id in sorted(set(results) - known):
        unexpected.append({"trial_id": trial_id, "error": "UNPLANNED_TRIAL_NOT_SCORED"})
    for plan in PLAN:
        row = {**plan, "status": "MISSING", "metrics": None, "error": None,
               "world_uuid": None, "episode": None, "matched_initial_manifest_sha256": None}
        found = results.get(plan["trial_id"], [])
        if not found:
            row["status"] = "NOT_RUN" if plans.get(plan["trial_id"]) else "MISSING"
            row["error"] = "No terminal trial result; retained in planned denominator"
        elif len(found) != 1 or len(plans.get(plan["trial_id"], [])) != 1:
            row["status"] = "DUPLICATE_OR_AMBIGUOUS_ARTIFACT"
            row["error"] = "Multiple results/plans or missing predeclared plan; no rerun selected"
        else:
            path, result = found[0]
            row["artifact_result_path"] = str(path.relative_to(root))
            row["recorded_status"] = result.get("status")
            row["source_commit"] = result.get("source_commit")
            row["github_run_id"] = result.get("github_run_id")
            row["github_run_attempt"] = result.get("github_run_attempt")
            row["world_uuid"] = (result.get("world") or {}).get("world_uuid")
            row["episode"] = result.get("fixture", {}).get("final", {}).get("episode")
            row["matched_initial_manifest_sha256"] = result.get("matched_initial_manifest_sha256")
            if result.get("status") != "VALID_OBSERVATION":
                row["status"] = result.get("status", "INVALID_ARTIFACT")
                row["error"] = result.get("error") or result.get("runner_error") or "Trial did not finish"
                row["partial_outcome"] = result.get("fixture", {}).get("inventories_after")
            else:
                try:
                    row["metrics"], row["verified_evidence_files"] = validate_result(
                        result, plan, path.parent, repo, expected_commit)
                    row["status"] = "VALID_OBSERVATION"
                except Exception as error:
                    row["status"] = "INVALID_EVIDENCE"
                    row["error"] = type(error).__name__ + ": " + str(error)
        rows.append(row)
    for key in ("world_uuid", "episode"):
        groups = {}
        for row in rows:
            if row[key] is not None:
                groups.setdefault(row[key], []).append(row)
        for group in groups.values():
            if len(group) > 1:
                for row in group:
                    row["status"] = "REUSED_WORLD_OR_SESSION"
                    row["error"] = "Independent-world identity repeated across planned trials"
    result = paired_summary(rows)
    result.update(expected_commit=expected_commit, protocol_sha256=protocol_hash(repo),
                  unexpected_artifacts=unexpected)
    result["all_planned_protocol_gates_passed"] = result["valid_world_observations"] == len(PLAN) and not unexpected
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.root, Path(__file__).resolve().parents[1], args.expected_commit)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("planned_worlds", "valid_world_observations", "planned_pairs",
          "valid_paired_observations", "primary_paired_deltas", "mechanism_coverage", "all_planned_protocol_gates_passed")},
          indent=2, sort_keys=True))
    raise SystemExit(0 if result["all_planned_protocol_gates_passed"] else 1)
