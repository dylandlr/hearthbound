#!/usr/bin/env python3
"""Verify every engineering slot; valid output and exercised capabilities are separate."""
import argparse
from collections import Counter
from datetime import datetime
import gzip
import hashlib
import json
import os
from pathlib import Path

from network_qualification_protocol import (
    CAPABILITY_REQUIREMENTS, DESIGN_SHA256, LEDGER_SCHEMA, PLAN, SCHEMA, SUMMARY_SCHEMA,
    context, digest, load_json, plan_document, protocol_hash,
)
from network_qualification_native import verify_native_history
from rcon_network_qualification import replay_transcript, require, uuid, validate_trial
from run_colony_reliability_trial import NbtReader
from run_network_qualification import validate_build_record


def verify_ledger(directory):
    ledger = load_json(directory / "evidence-sha256.json")
    require(set(ledger) == {"schema", "files"} and ledger["schema"] == LEDGER_SCHEMA
            and isinstance(ledger["files"], dict), "Invalid qualification evidence ledger")
    required = {"planned-trial.json", "world-attempt.json", "trial-result.json", "forge-server.log", "rcon.log",
                "world-metadata/level.dat", "world-metadata/hearthbound_world_identity_v1.dat",
                "world-metadata/hearthbound_citizen_communication_v1.dat", "build-evidence/preflight.json",
                "build-evidence/build-environment.json", "build-evidence/preflight.log",
                "build-evidence/java-version.log", "build-evidence/gradle-version.log"}
    require(required <= set(ledger["files"]), "Mandatory native/build evidence omitted")
    actual = {str(path.relative_to(directory)) for path in directory.rglob("*")
              if path.is_file() and path.name != "evidence-sha256.json"}
    require(actual == set(ledger["files"]), "Qualification ledger omitted or added a retained file")
    for name, expected in ledger["files"].items():
        relative = Path(name)
        require(not relative.is_absolute() and ".." not in relative.parts, "Unsafe evidence path")
        path = directory / relative
        require(path.is_file() and not path.is_symlink()
                and hashlib.sha256(path.read_bytes()).hexdigest() == expected, "Evidence digest mismatch: " + name)
    return len(actual)


def validate_plan(planned, repo, trial_id, expected_commit, expected_context):
    require(expected_context["run_attempt"] == "1"
            and all(isinstance(expected_context[key], str) and expected_context[key] for key in ("workflow", "run_id")),
            "Provide independently verified first-run context for replay")
    expected = plan_document(repo, trial_id, planned["declaration_utc"], expected_context)
    require(planned == expected and planned["source_commit"] == expected_commit
            and planned["declaration_utc"] is not None, "Qualification declaration/source/context mismatch")


def validate_result(result, plan, directory, repo, expected_commit, expected_context):
    planned = load_json(directory / "planned-trial.json")
    validate_plan(planned, repo, plan["trial_id"], expected_commit, expected_context)
    require(result["schema"] == SCHEMA and result["status"] == "VALID_OBSERVATION"
            and result["protocol_valid"] is True, "Qualification did not produce valid complete evidence")
    for key in ("trial_id", "block_id", "seed", "arm", "policy_seed", "source_commit", "source_tree",
                "protocol_sha256", "initial_manifest_sha256", "execution_context"):
        require(result[key] == planned[key], "Result differs from prospective plan: " + key)
    require(result["github_run_id"] == expected_context["run_id"]
            and result["github_run_attempt"] == "1" and result["behavioral_retries"] == 0
            and result["fresh_world_directory"] is True and result["planned_worlds"] == 6
            and result["qualification_only"] is True and result["expanded_study_worlds"] == 0
            and result["clean_server_exit"] is True and result["server_exit_code"] == 0
            and result["phase"] == result["last_runner_phase"] == "FINISHED"
            and result["error_type"] is None and result["error"] is None and not result["secondary_errors"]
            and result["communication_win_required"] is False and result["causal_benefit_established"] is False
            and result["learned_collaboration"] is False and result["reward_authorized"] is False,
            "Qualification execution/inference contract changed")
    files = verify_ledger(directory)
    reservation = load_json(directory / "world-attempt.json")
    require(set(reservation) == {"schema", "trial_id", "source_commit", "plan_sha256", "execution_context", "reserved_utc", "attempt"}
            and reservation["schema"] == "hearthbound.network-qualification-attempt.v1"
            and reservation["trial_id"] == plan["trial_id"] and reservation["source_commit"] == expected_commit
            and reservation["plan_sha256"] == digest(planned) and reservation["execution_context"] == expected_context
            and reservation["attempt"] == 1, "One-shot world reservation invalid")
    build = validate_build_record(repo, planned, directory / "build-evidence")
    require(result["build_evidence"] == build, "Recorded build evidence differs from independent replay")
    preflight = load_json(directory / "build-evidence/preflight.json")
    require(datetime.fromisoformat(preflight["finished_at"].replace("Z", "+00:00"))
            <= datetime.fromisoformat(reservation["reserved_utc"]), "World reserved before successful dependency setup")
    metadata = directory / "world-metadata"
    level_bytes = (metadata / "level.dat").read_bytes()
    identity_bytes = (metadata / "hearthbound_world_identity_v1.dat").read_bytes()
    level = NbtReader(gzip.decompress(level_bytes)).root()["Data"]
    identity = NbtReader(gzip.decompress(identity_bytes)).root()["data"]
    world = result["world"]
    require(world["generated_seed"] == plan["seed"] == level["WorldGenSettings"]["seed"]
            and world["configured_seed"] == str(plan["seed"])
            and world["world_uuid"] == uuid(identity["worldUuid"]) == result["fixture"]["final"]["world"]
            and world["level_name"] == level["LevelName"] == "network-qualification-" + plan["trial_id"]
            and world["origin"] == "PERSISTED_FORGE_LEVEL_DAT_AND_HEARTHBOUND_SAVEDDATA",
            "Native world identity/seed/origin differs from declared slot")
    require(world["level_dat_sha256"] == hashlib.sha256(level_bytes).hexdigest()
            and world["world_identity_sha256"] == hashlib.sha256(identity_bytes).hexdigest(), "Native metadata digest mismatch")
    for field, name in (("server_log_sha256", "forge-server.log"), ("rcon_log_sha256", "rcon.log")):
        require(result[field] == hashlib.sha256((directory / name).read_bytes()).hexdigest(), "Log digest mismatch")
    metrics = validate_trial(result["fixture"], plan["seed"], plan["arm"])
    require(metrics == result["fixture"]["metrics"], "Recorded metrics differ from qualification replay")
    native = verify_native_history(metadata / "hearthbound_citizen_communication_v1.dat",
                                   result["fixture"]["communication"], result["fixture"]["records"])
    transcript = replay_transcript((directory / "rcon.log").read_text(), result["fixture"], plan["seed"], plan["arm"])
    return metrics, {"verified_files": files, "native_communication": native, "transcript": transcript,
                     "build": build, "declaration_precedes_setup": True, "one_shot_reservation_verified": True}


def capability_coverage(arm, metrics):
    comm, net = metrics["communication"], metrics["network"]
    values = {"network_disabled_attempts": net["network_disabled_attempts"],
              "topology_blocked_attempts": net["topology_blocked_attempts"],
              "allowed_transport_attempts": net["allowed_transport_attempts"],
              "deliveries": comm["delivered_messages"], "policy_reads": comm["policy_reads"],
              "selections": comm["selected_reports"], "report_cued_assignments": comm["report_cued_assignments"],
              "report_cued_completions": comm["report_cued_physical_jobs"]}
    unmet = []
    for field, expected in CAPABILITY_REQUIREMENTS[arm].items():
        actual = values[field[:-4] if field.endswith("_min") else field]
        passed = actual >= expected if field.endswith("_min") else actual == expected
        if not passed:
            unmet.append(field)
    return {"status": "EXERCISED" if not unmet else "NOT_EXERCISED", "requirements": CAPABILITY_REQUIREMENTS[arm],
            "observed": values, "unmet_requirements": unmet,
            "coverage_distinct_from_validity": True, "absence_allows_replacement": False}


def qualification_summary(rows, unexpected):
    require(len(rows) == len(PLAN) and [row["trial_id"] for row in rows] == [row["trial_id"] for row in PLAN],
            "Qualification denominator/order changed")
    valid = [row for row in rows if row["status"] == "VALID_OBSERVATION"]
    exercised = [row for row in valid if row["capability"]["status"] == "EXERCISED"]
    return {"schema": SUMMARY_SCHEMA, "design_sha256": DESIGN_SHA256,
            "planned_worlds": 6, "valid_world_observations": len(valid), "invalid_or_missing_worlds": 6 - len(valid),
            "status_counts": dict(Counter(row["status"] for row in rows)), "worlds": rows,
            "capability_requirements": CAPABILITY_REQUIREMENTS, "capabilities_exercised": len(exercised),
            "all_planned_protocol_gates_passed": len(valid) == 6 and not unexpected,
            "all_required_live_capabilities_exercised": len(exercised) == 6 and not unexpected,
            "qualification_gate_passed": len(valid) == len(exercised) == 6 and not unexpected,
            "qualification_only": True, "expanded_study_worlds": 0, "expanded_study_execution_authorized": False,
            "inference_scope": "ENGINEERING_CAPABILITY_QUALIFICATION_ONLY", "performance_win_required": False,
            "population_effect_estimated": False, "topology_winner_selected": False,
            "causal_benefit_established": False, "learned_collaboration": False, "llm_control": False,
            "original_accounting_or_active_haul_failure_frequency_estimated": False,
            "previous_cohorts_pooled": False, "unexpected_artifacts": unexpected}


def summarize(root, repo, expected_commit, expected_context=None):
    expected_context = context() if expected_context is None else expected_context
    results, plans, unexpected = {}, {}, []
    for filename, collection in (("trial-result.json", results), ("planned-trial.json", plans)):
        for path in sorted(root.rglob(filename)) if root.exists() else []:
            try:
                value = load_json(path)
                collection.setdefault(value["trial_id"], []).append((path, value))
            except Exception as error:
                unexpected.append({"path": str(path.relative_to(root)), "error": type(error).__name__ + ": " + str(error)})
    known = {plan["trial_id"] for plan in PLAN}
    for trial in sorted((set(results) | set(plans)) - known):
        unexpected.append({"trial_id": trial, "error": "UNPLANNED_QUALIFICATION_SLOT"})
    rows = []
    for plan in PLAN:
        row = {**plan, "status": "MISSING_ARTIFACTS", "metrics": None, "capability": None,
               "world_uuid": None, "episode": None, "error": None}
        found, declared = results.get(plan["trial_id"], []), plans.get(plan["trial_id"], [])
        try:
            if len(found) > 1 or len(declared) > 1:
                raise ValueError("Multiple results/plans; no replacement or best attempt selected")
            if len(declared) != 1:
                raise ValueError("Prospective declaration missing")
            plan_path, saved = declared[0]
            validate_plan(saved, repo, plan["trial_id"], expected_commit, expected_context)
            if not found:
                row.update(status="NOT_RUN_BEFORE_RUNTIME", error="Declared slot has no runtime result; reason and physical outcome unknown")
            else:
                path, result = found[0]
                require(path.parent == plan_path.parent, "Plan/result artifacts are not colocated")
                recorded_world = (result.get("world") or {}).get("world_uuid")
                recorded_episode = result.get("fixture", {}).get("final", {}).get("episode")
                # Normalize before publishing identities to cross-slot deduplication.
                # A malformed failed row must not prevent the six-slot summary.
                recorded_world = None if recorded_world is None else uuid(recorded_world)
                recorded_episode = None if recorded_episode is None else uuid(recorded_episode)
                row.update(recorded_status=result.get("status"), source_commit=result.get("source_commit"),
                           github_run_id=result.get("github_run_id"), github_run_attempt=result.get("github_run_attempt"),
                           world_uuid=recorded_world, episode=recorded_episode)
                require(result.get("schema") == SCHEMA, "Failed or valid result schema changed")
                for key in ("trial_id", "block_id", "seed", "arm", "policy_seed", "source_commit", "source_tree",
                            "protocol_sha256", "initial_manifest_sha256", "execution_context"):
                    require(result.get(key) == saved[key], "Failed or valid result scope changed: " + key)
                require(result.get("github_run_id") == expected_context["run_id"]
                        and result.get("github_run_attempt") == "1", "Failed or valid result workflow changed")
                if result.get("status") != "VALID_OBSERVATION":
                    require(result.get("status") in {"STARTING", "RUNNING", "INVALID_OBSERVATION",
                            "NOT_RUN_BEFORE_RUNTIME", "INFRASTRUCTURE_FAILURE", "EVIDENCE_FAILURE"}, "Unknown recorded failure status")
                    row.update(status=result["status"],
                               error=result.get("error") or "Slot has no valid fixed-horizon observation")
                else:
                    metrics, verification = validate_result(result, plan, path.parent, repo, expected_commit, expected_context)
                    row.update(status="VALID_OBSERVATION", metrics=metrics, verification=verification,
                               capability=capability_coverage(plan["arm"], metrics))
        except Exception as error:
            row.update(status="INVALID_EVIDENCE" if found or declared else "MISSING_ARTIFACTS",
                       error=type(error).__name__ + ": " + str(error), metrics=None, capability=None)
        rows.append(row)
    for field in ("world_uuid", "episode"):
        repeated = {row[field] for row in rows if row[field] is not None
                    and sum(other[field] == row[field] for other in rows) > 1}
        for row in rows:
            if row[field] in repeated:
                row.update(status="REUSED_WORLD_OR_SESSION", metrics=None, capability=None,
                           error="Native world/session repeated across qualification slots")
    result = qualification_summary(rows, unexpected)
    result.update(expected_commit=expected_commit, expected_execution_context=expected_context,
                  protocol_sha256=protocol_hash(repo))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--expected-commit", required=True)
    parser.add_argument("--expected-run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument("--expected-workflow", default=os.environ.get("GITHUB_WORKFLOW"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    expected = {"workflow": args.expected_workflow, "run_id": args.expected_run_id, "run_attempt": "1"}
    result = summarize(args.root, Path(__file__).resolve().parents[1], args.expected_commit, expected)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("planned_worlds", "valid_world_observations", "status_counts",
          "capabilities_exercised", "all_planned_protocol_gates_passed", "qualification_gate_passed")}, indent=2))
    raise SystemExit(0 if result["qualification_gate_passed"] else 1)
