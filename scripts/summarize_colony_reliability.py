#!/usr/bin/env python3
"""Keep every planned fresh-world trial in the reliability denominator.

The interval is a descriptive binomial interval for this fixed fixture/seed
cohort. It is not evidence that the unresolved accounting defect is fixed.
"""
import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from uuid import UUID

import colony_motor_diagnostics as motor_diagnostics

TRIAL_SCHEMA = "hearthbound.colony-reliability-trial.v1"
PLAN_SCHEMA = "hearthbound.colony-reliability-plan.v1"
SUMMARY_SCHEMA = "hearthbound.colony-reliability-summary.v1"
PLAN = tuple({"trial_id": f"world-{i:02d}", "seed": 43100 + i}
             for i in range(1, 6))
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")
WORKFLOW_ID = re.compile(r"[1-9][0-9]*")
TERMINAL_STATUSES = {
    "PASS", "ACCOUNTING_THREE_OF_FOUR", "TASK_ACCOUNTING_MISMATCH",
    "FIXTURE_ASSERTION_FAILURE", "INFRASTRUCTURE_FAILURE", "INVALID_EVIDENCE",
}
PROTOCOL_FILES = (
    "build.gradle",
    "settings.gradle",
    "gradle.properties",
    "gradle/forge-build-environment.gradle",
    "gradle/force-forge-tool-fallback.init.gradle",
    "scripts/run_forge_build_preflight.py",
    "scripts/rcon_civilization_four_citizens.py",
    "scripts/rcon_two_citizen_haul_acceptance.py",
    "scripts/run_colony_reliability_trial.py",
    "scripts/summarize_colony_reliability.py",
    "scripts/colony_motor_diagnostics.py",
    "scripts/haul_motor_diagnostics.py",
    "src/main/java/dev/hearthbound/world/HaulMotorDiagnostics.java",
    "src/main/java/dev/hearthbound/world/HaulClaims.java",
    "src/main/java/dev/hearthbound/world/HearthboundWorldIdentity.java",
    ".github/workflows/real-colony-reliability.yml",
)


def protocol_hash(repo):
    """Pin build inputs, fixture, runner, aggregation rules, and cohort workflow."""
    digest = hashlib.sha256()
    for name in PROTOCOL_FILES:
        digest.update(name.encode() + b"\0")
        digest.update((Path(repo) / name).read_bytes() + b"\0")
    return digest.hexdigest()


def plan_hash(document):
    """Bind the complete canonical declaration, including its workflow attempt."""
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def plan_errors(document, expected, expected_commit=None, expected_protocol=None,
                expected_run_id=None, expected_run_attempt=None):
    """Validate prospective intent without treating it as a world observation."""
    errors = []
    if not isinstance(document, dict):
        return ["prospective plan is not an object"]
    if document.get("schema") != PLAN_SCHEMA:
        errors.append("wrong prospective plan schema")
    if (document.get("trial_id") != expected["trial_id"]
            or type(document.get("seed")) is not int
            or document.get("seed") != expected["seed"]):
        errors.append("prospective trial/seed differs from predeclared cohort")
    if (not isinstance(document.get("source_commit"), str)
            or not SHA.fullmatch(document["source_commit"])):
        errors.append("missing prospective source commit")
    elif expected_commit and document["source_commit"] != expected_commit:
        errors.append("prospective source commit differs from requested commit")
    if (not isinstance(document.get("protocol_sha256"), str)
            or not HASH.fullmatch(document["protocol_sha256"])):
        errors.append("missing prospective protocol hash")
    elif expected_protocol and document["protocol_sha256"] != expected_protocol:
        errors.append("prospective protocol differs from checked-out inputs")
    if document.get("level_name") != "colony-reliability-" + expected["trial_id"]:
        errors.append("wrong prospective world name")
    if (document.get("declaration_phase") != "BEFORE_BUILD_PREFLIGHT"
            or document.get("execution_policy") != "ONE_ATTEMPT_PER_PLANNED_WORLD"
            or document.get("fresh_world_required") is not True
            or document.get("motor_diagnostics_required") is not True):
        errors.append("prospective execution requirements changed")
    for field, trusted in (("github_run_id", expected_run_id),
                           ("github_run_attempt", expected_run_attempt)):
        value = document.get(field)
        if field not in document or (value is not None
                and (not isinstance(value, str) or not WORKFLOW_ID.fullmatch(value))):
            errors.append("invalid prospective workflow identity: " + field)
        if trusted is not None and value != trusted:
            errors.append("prospective workflow identity differs from requested context: " + field)
    if any(field in document for field in ("world", "world_uuid", "terminal_snapshot",
                                           "fixture_passed", "observation_window_completed")):
        errors.append("prospective declaration contains claimed world observations")
    try:
        plan_hash(document)
    except (TypeError, ValueError):
        errors.append("prospective declaration is not canonical JSON")
    return errors


def result_shape_errors(record):
    """Validate consumed JSON types before hashing, membership, or inspection.

    Missing optional fields remain the semantic validator's responsibility.
    A malformed field never becomes a replacement value or a zero observation.
    """
    if not isinstance(record, dict):
        return ["result is not an object"]
    errors = []
    required = {
        "schema": str, "trial_id": str, "seed": int, "source_commit": str,
        "protocol_sha256": str, "status": str, "fixture_passed": bool,
        "observation_window_completed": bool, "fresh_world_directory": bool,
    }
    optional = {
        "world": dict, "terminal_snapshot": (dict, type(None)),
        "error_type": (str, type(None)), "rcon_log_sha256": str,
        "server_log_sha256": str, "github_run_id": (str, type(None)),
        "github_run_attempt": (str, type(None)), "prospective_plan_sha256": (str, type(None)),
        "motor_diagnostics_required": bool, "prospective_plan_required": bool,
        "motor_diagnostics": dict, "verified_motor_diagnostics": dict,
    }
    for field, allowed in {**required, **optional}.items():
        if field in required or field in record:
            allowed_types = allowed if isinstance(allowed, tuple) else (allowed,)
            if type(record.get(field)) not in allowed_types:
                errors.append("invalid result field type: " + field)
    retained_errors = record.get("artifact_validation_errors", [])
    if (not isinstance(retained_errors, list)
            or any(not isinstance(value, str) for value in retained_errors)):
        errors.append("invalid result field type: artifact_validation_errors")
    world = record.get("world")
    if isinstance(world, dict):
        for field, kind in (("world_uuid", str), ("generated_seed", int),
                            ("configured_seed", str), ("level_name", str),
                            ("level_dat_sha256", str), ("world_identity_sha256", str)):
            if field in world and type(world[field]) is not kind:
                errors.append("invalid result field type: world." + field)
    verified = record.get("verified_motor_diagnostics")
    if isinstance(verified, dict):
        if not isinstance(verified.get("status"), str):
            errors.append("invalid verified diagnostic status")
        findings = verified.get("findings")
        if (not isinstance(findings, list) or any(
                not isinstance(finding, dict)
                or not isinstance(finding.get("flags", []), list)
                or any(not isinstance(flag, str) for flag in finding.get("flags", []))
                for finding in findings)):
            errors.append("invalid verified diagnostic findings")
    return errors


def index_artifacts(artifacts, expected_ids, kind, errors, invalid_artifacts):
    """Retain unassignable and duplicate inputs without selecting a replacement."""
    indexed = {}
    for index, document in enumerate(artifacts):
        trial_id = document.get("trial_id") if isinstance(document, dict) else None
        reason = None
        if not isinstance(document, dict):
            reason = kind + " is not an object"
        elif not isinstance(trial_id, str):
            reason = kind + " has non-string trial_id"
        elif trial_id not in expected_ids:
            reason = "unexpected " + ("trial" if kind == "result" else "prospective plan") + ": " + trial_id
        elif trial_id in indexed:
            reason = "duplicate " + ("trial result" if kind == "result" else "prospective plan") + ": " + trial_id
        if reason is not None:
            errors.append(reason)
            invalid_artifacts.append({"kind": kind, "input_index": index,
                                      "trial_id": trial_id if isinstance(trial_id, str) else None,
                                      "error": reason})
        else:
            indexed[trial_id] = document
    return indexed


def validation_context(expected_commit, expected_protocol, expected_run_id,
                       expected_run_attempt, plans_required):
    """Caller-supplied expectations are separate from artifact self-reporting.

    Offline callers may inspect historical data without this context, but that
    descriptive calculation cannot certify workflow acceptance. The caller must
    obtain expected values from a trusted checkout/run, not from these records.
    """
    expected = {"source_commit": expected_commit, "protocol_sha256": expected_protocol,
                "github_run_id": expected_run_id, "github_run_attempt": expected_run_attempt}
    patterns = {"source_commit": SHA, "protocol_sha256": HASH,
                "github_run_id": WORKFLOW_ID, "github_run_attempt": WORKFLOW_ID}
    errors = ["trusted expected " + field + " is missing or invalid"
              for field, value in expected.items()
              if not isinstance(value, str) or not patterns[field].fullmatch(value)]
    if not plans_required:
        errors.append("prospective plans are not required by the acceptance context")
    return {"status": "VERIFIED_EXPECTATIONS" if not errors else "DESCRIPTIVE_ONLY",
            "expected": {key: value if isinstance(value, str) else None
                         for key, value in expected.items()},
            "errors": errors,
            "artifact_identity_is_not_trusted_context": True}


def artifact_json(text):
    """Reject ambiguous JSON objects before any field can overwrite another."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate JSON key: " + key)
            result[key] = value
        return result
    return json.loads(text, object_pairs_hook=unique_object)


def wilson(successes, total):
    if not 0 <= successes <= total:
        raise ValueError("Invalid binomial counts")
    if total == 0:
        return None
    z = 1.959963984540054
    p = successes / total
    denominator = 1 + z * z / total
    center = (p + z * z / (2 * total)) / denominator
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denominator
    return [max(0.0, center - half), min(1.0, center + half)]


def counters(text, marker):
    if not isinstance(text, str) or marker not in text:
        return None
    return {key: int(value) for key, value in
            re.findall(r"\b([a-z_]+)=(\d+)\b", text.split(marker, 1)[1])}


def snapshot_valid(snapshot):
    if not isinstance(snapshot, dict):
        return False
    return (
        all(isinstance(snapshot.get(key), dict)
            and all(type(snapshot[key].get(field)) is int
                    and snapshot[key][field] >= 0
                    for field in ("done", "assigned", "held", "queued"))
            for key in ("audit_before", "audit_after"))
        and type(snapshot.get("destination_has_exact_four_wheat")) is bool
        and isinstance(snapshot.get("source_wheat_absent"), list)
        and len(snapshot["source_wheat_absent"]) == 4
        and all(type(value) is bool for value in snapshot["source_wheat_absent"])
        and type(snapshot.get("outstanding_claims")) is int
        and snapshot["outstanding_claims"] >= 0
        and isinstance(snapshot.get("history"), dict)
        and all(type(snapshot["history"].get(field)) is int
                and snapshot["history"][field] >= 0
                for field in ("records", "physically_completed", "capacity_denials"))
    )


def physical_four(snapshot):
    return (snapshot_valid(snapshot)
            and snapshot["destination_has_exact_four_wheat"]
            and all(snapshot["source_wheat_absent"])
            and snapshot["outstanding_claims"] == 0)


def accounting_three_of_four(snapshot):
    """Require agreement of both audit reads bracketing the physical probes."""
    return (physical_four(snapshot)
            and all(snapshot[key]["done"] == 3 and snapshot[key]["assigned"] == 1
                    for key in ("audit_before", "audit_after")))


def physical_delivery_accounting(snapshot):
    """Additional prospective event; never redefine the original 3/1 event.

    Return None when non-atomic probes disagree or fixture task counters cannot
    describe its four one-item jobs. Such evidence cannot establish either the
    presence or absence of this stable pending-assignment signature. The caller
    additionally requires a complete observation window and valid provenance.
    """
    if not snapshot_valid(snapshot):
        return None
    before, after = snapshot["audit_before"], snapshot["audit_after"]
    fields = ("done", "assigned", "held", "queued")
    if any(before[field] != after[field] for field in fields):
        return None
    if sum(after[field] for field in fields) > 4:
        return None
    for audit in (before, after):
        distinct = audit.get("distinct_completed_citizens")
        if distinct is not None and (type(distinct) is not int
                                     or not 0 <= distinct <= audit["done"]):
            return None
    return (physical_four(snapshot)
            and after["done"] < 4 and after["assigned"] > 0)


def diagnostic_flags(snapshot):
    """Descriptive terminal patterns; do not change preregistered pass/fail classes."""
    if not snapshot_valid(snapshot):
        return []
    before, after = snapshot["audit_before"], snapshot["audit_after"]
    flags = []
    if accounting_three_of_four(snapshot):
        flags.append("PHYSICAL_FOUR_TASK_THREE_ASSIGNED_ONE")
    if (physical_four(snapshot) and before["done"] == after["done"] == 4
            and before["assigned"] == after["assigned"] == 0
            and type(after.get("distinct_completed_citizens")) is int
            and after["distinct_completed_citizens"] < 4):
        flags.append("FOUR_DELIVERIES_FEWER_THAN_FOUR_CITIZENS")
    if (not snapshot["destination_has_exact_four_wheat"]
            and not all(snapshot["source_wheat_absent"])
            and before["done"] == after["done"] < 4
            and before["assigned"] == after["assigned"] == 0):
        flags.append("SOURCE_REMAINS_NO_ASSIGNED_TASK")
    return flags


def classified_status(fixture_passed, full_window, error_type, snapshot):
    if fixture_passed:
        # A pass marker alone is never sufficient to promote a trial.
        if (not physical_four(snapshot)
                or any(snapshot[key][field] != expected
                       for key in ("audit_before", "audit_after")
                       for field, expected in (("done", 4), ("assigned", 0),
                                               ("held", 0), ("queued", 0)))
                or snapshot["history"]["records"] != 4
                or snapshot["history"]["physically_completed"] != 4
                or snapshot["history"]["capacity_denials"] != 0):
            return "INVALID_EVIDENCE"
        return "PASS"
    if full_window and accounting_three_of_four(snapshot):
        return "ACCOUNTING_THREE_OF_FOUR"
    if full_window and physical_four(snapshot) and (
            snapshot["audit_after"]["done"] != 4
            or snapshot["audit_after"]["assigned"] != 0
            or snapshot["history"]["physically_completed"] != 4):
        return "TASK_ACCOUNTING_MISMATCH"
    if error_type == "AssertionError":
        return "FIXTURE_ASSERTION_FAILURE"
    return "INFRASTRUCTURE_FAILURE"


def result_errors(record, expected, expected_commit=None,
                  expected_run_id=None, expected_run_attempt=None):
    shape_errors = result_shape_errors(record)
    if shape_errors:
        return shape_errors
    errors = list(record.get("artifact_validation_errors", []))
    if record.get("schema") != TRIAL_SCHEMA:
        errors.append("wrong schema")
    if record.get("trial_id") != expected["trial_id"] or record.get("seed") != expected["seed"]:
        errors.append("trial/seed differs from predeclared plan")
    if not SHA.fullmatch(str(record.get("source_commit", ""))):
        errors.append("missing tested commit")
    elif expected_commit and record["source_commit"] != expected_commit:
        errors.append("tested commit differs from requested commit")
    if not HASH.fullmatch(str(record.get("protocol_sha256", ""))):
        errors.append("missing protocol hash")
    for field, trusted in (("github_run_id", expected_run_id),
                           ("github_run_attempt", expected_run_attempt)):
        if trusted is not None and record.get(field) != trusted:
            errors.append("result workflow identity differs from requested context: " + field)
    if record.get("status") not in TERMINAL_STATUSES:
        errors.append("unfinished or unknown status")
    if record.get("fresh_world_directory") is not True:
        errors.append("fresh world directory was not verified")
    if record.get("status") == "PASS" or record.get("observation_window_completed") is True:
        for key in ("rcon_log_sha256", "server_log_sha256"):
            if not HASH.fullmatch(str(record.get(key, ""))):
                errors.append("missing retained log hash")
        world = record.get("world", {})
        if not isinstance(world, dict):
            world = {}
            errors.append("malformed persisted world evidence")
        try:
            UUID(world.get("world_uuid", ""))
        except (AttributeError, TypeError, ValueError):
            errors.append("missing persisted world UUID")
        if world.get("generated_seed") != expected["seed"]:
            errors.append("persisted generated seed mismatch")
        if world.get("configured_seed") != str(expected["seed"]):
            errors.append("configured seed mismatch")
        if world.get("level_name") != "colony-reliability-" + expected["trial_id"]:
            errors.append("wrong fresh world name")
        for key in ("level_dat_sha256", "world_identity_sha256"):
            if not HASH.fullmatch(str(world.get(key, ""))):
                errors.append("missing persisted world evidence hash")
        if not snapshot_valid(record.get("terminal_snapshot")):
            errors.append("incomplete terminal observation")
    expected_status = classified_status(
        record.get("fixture_passed") is True,
        record.get("observation_window_completed") is True,
        record.get("error_type"), record.get("terminal_snapshot"))
    if record.get("status") not in (expected_status, "INVALID_EVIDENCE"):
        errors.append("status disagrees with observed evidence")
    if record.get("status") == "PASS" and record.get("fixture_passed") is not True:
        errors.append("pass without a completed acceptance fixture")
    if record.get("status") == "PASS" and record.get("observation_window_completed") is not True:
        errors.append("pass without a complete observation window")
    return errors


def summarize(records, plan=PLAN, expected_commit=None, require_motor_diagnostics=False,
              prospective_plans=(), require_prospective_plans=False, expected_protocol=None,
              expected_run_id=None, expected_run_attempt=None):
    errors = []
    invalid_artifacts = []
    expected_ids = {item["trial_id"] for item in plan}
    by_id = index_artifacts(records, expected_ids, "result", errors, invalid_artifacts)
    declarations = index_artifacts(prospective_plans, expected_ids, "plan", errors, invalid_artifacts)
    normalized = []
    world_ids = set()
    commits, protocols = set(), set()
    workflow_attempts = set()
    motor_diagnostics_required = (require_motor_diagnostics or any(
        isinstance(record, dict) and record.get("motor_diagnostics_required") is True
        for record in records) or any(
        isinstance(document, dict) and document.get("motor_diagnostics_required") is True
        for document in prospective_plans))
    plans_required = (require_prospective_plans or bool(prospective_plans) or any(
        isinstance(record, dict) and record.get("prospective_plan_required") is True
        for record in records))
    context = validation_context(expected_commit, expected_protocol, expected_run_id,
                                 expected_run_attempt, plans_required)
    for item in plan:
        declaration = declarations.get(item["trial_id"])
        invalid_plan = (plan_errors(declaration, item, expected_commit, expected_protocol,
                                    expected_run_id, expected_run_attempt)
                        if declaration is not None else
                        ["missing prospective plan"] if plans_required else [])
        plan_status = ("INVALID" if declaration is not None and invalid_plan else
                       "VERIFIED" if declaration is not None else
                       "MISSING" if plans_required else "NOT_REQUIRED_FOR_THIS_REVISION")
        plan_detail = {"status": plan_status, "errors": invalid_plan}
        if declaration is not None and not invalid_plan:
            plan_detail.update(sha256=plan_hash(declaration),
                               source_commit=declaration["source_commit"],
                               protocol_sha256=declaration["protocol_sha256"],
                               github_run_id=declaration["github_run_id"],
                               github_run_attempt=declaration["github_run_attempt"])
            commits.add(declaration["source_commit"])
            protocols.add(declaration["protocol_sha256"])
            workflow_attempts.add((declaration["github_run_id"], declaration["github_run_attempt"]))
        record = by_id.get(item["trial_id"])
        if record is None:
            normalized.append({**item,
                               "status": "NOT_RUN" if plan_status == "VERIFIED" else
                                   "INVALID_EVIDENCE" if declaration is not None else "MISSING_RESULT",
                               "accounting_event_observed": None,
                               "physical_delivery_accounting_event_observed": None,
                               "motor_diagnostics": {"status": "MISSING_TRIAL", "findings": []},
                               "prospective_plan": plan_detail,
                               "errors": ["no trial result; world creation and outcome are unobserved"]
                                   + invalid_plan})
            continue
        invalid = result_errors(record, item, expected_commit,
                                expected_run_id, expected_run_attempt) + invalid_plan
        if declaration is not None and not invalid_plan:
            if record.get("prospective_plan_sha256") != plan_detail["sha256"]:
                invalid.append("result is not bound to retained prospective plan")
            for field in ("source_commit", "protocol_sha256", "github_run_id", "github_run_attempt"):
                if record.get(field) != declaration[field]:
                    invalid.append("result differs from prospective plan: " + field)
        world = record.get("world", {})
        world_id = world.get("world_uuid") if isinstance(world, dict) else None
        if not isinstance(world_id, str):
            world_id = None
        if world_id:
            canonical = str(world_id).lower()
            if canonical in world_ids:
                invalid.append("persisted world UUID reused")
            world_ids.add(canonical)
        if isinstance(record.get("source_commit"), str) and record["source_commit"]:
            commits.add(record["source_commit"])
        if isinstance(record.get("protocol_sha256"), str) and record["protocol_sha256"]:
            protocols.add(record["protocol_sha256"])
        eligible = (not invalid and record["status"] != "INVALID_EVIDENCE"
                    and record.get("observation_window_completed") is True
                    and snapshot_valid(record.get("terminal_snapshot")))
        normalized.append({
            **item, "status": "INVALID_EVIDENCE" if invalid else record["status"],
            "world_uuid": world_id,
            "diagnostic_flags": diagnostic_flags(record.get("terminal_snapshot"))
                if not invalid and snapshot_valid(record.get("terminal_snapshot")) else [],
            "accounting_event_observed": accounting_three_of_four(record["terminal_snapshot"])
                if eligible else None,
            "physical_delivery_accounting_event_observed":
                physical_delivery_accounting(record["terminal_snapshot"])
                if eligible else None,
            "errors": invalid,
            "prospective_plan": plan_detail,
            "motor_diagnostics": {"status": "INVALID_WORLD_PROVENANCE", "findings": []}
                if invalid else record.get("verified_motor_diagnostics", {
                "status": "NOT_VERIFIED" if motor_diagnostics_required
                else "NOT_REQUIRED_FOR_THIS_REVISION", "findings": []}),
        })
    if len(commits) > 1:
        errors.append("mixed tested commits")
    if len(protocols) > 1:
        errors.append("mixed protocols")
    if len(workflow_attempts) > 1:
        errors.append("mixed prospective workflow runs or attempts")
    # A duplicate, unexpected record, or mixed cohort invalidates the pooled
    # estimate instead of quietly dropping evidence until the number improves.
    if errors:
        for trial in normalized:
            trial["accounting_event_observed"] = None
            trial["physical_delivery_accounting_event_observed"] = None
            trial["motor_diagnostics"] = {"status": "INVALID_COHORT_PROVENANCE", "findings": []}
    diagnostic_counts = Counter(flag for item in normalized
                                for flag in item.get("diagnostic_flags", []))
    count = Counter(item["status"] for item in normalized)
    observed = sum(item["accounting_event_observed"] is True for item in normalized)
    assessed = sum(item["accounting_event_observed"] is not None for item in normalized)
    total = len(plan)
    unknown = total - assessed
    physical_observed = sum(item["physical_delivery_accounting_event_observed"] is True
                            for item in normalized)
    physical_assessed = sum(item["physical_delivery_accounting_event_observed"] is not None
                            for item in normalized)
    physical_unknown = total - physical_assessed
    motor_counts = Counter(item["motor_diagnostics"]["status"] for item in normalized)
    plan_counts = Counter(item["prospective_plan"]["status"] for item in normalized)
    motor_flags = Counter(flag for item in normalized
                          if item["motor_diagnostics"]["status"] == "VERIFIED_COMPLETE"
                          for finding in item["motor_diagnostics"].get("findings", [])
                          for flag in finding.get("flags", []))
    result = {
        "schema": SUMMARY_SCHEMA,
        "planned_trials": total,
        "received_unique_trials": len(by_id),
        "received_result_artifacts": len(records),
        "invalid_or_duplicate_artifacts": invalid_artifacts,
        "statuses": dict(sorted(count.items())),
        "terminal_diagnostic_patterns": dict(sorted(diagnostic_counts.items())),
        "all_trials_passed": not errors and count["PASS"] == total,
        "validation_context": context,
        "prospective_plans": {
            "required_for_cohort": plans_required,
            "planned_worlds": total,
            "statuses": dict(sorted(plan_counts.items())),
            "all_required_plans_verified": not plans_required
                or (not errors and plan_counts["VERIFIED"] == total),
            "declarations_are_world_observations": False,
            "no_result_outcomes_remain_unknown": True,
        },
        "post_window_motor_diagnostics": {
            "required_for_cohort": motor_diagnostics_required,
            "planned_worlds": total,
            "statuses": dict(sorted(motor_counts.items())),
            "all_required_worlds_verified": not motor_diagnostics_required
                or (not errors and motor_counts["VERIFIED_COMPLETE"] == total),
            "citizen_sequence_patterns": dict(sorted(motor_flags.items())),
            "patterns_are_diagnostics_not_independent_replicates": True,
            "original_score_recomputed": False,
            "root_cause_established": False,
        },
        "trials": normalized,
        "cohort_errors": errors,
        "source_commits": sorted(commits),
        "protocol_hashes": sorted(protocols),
        "three_of_four_accounting_event": {
            "observed": observed, "assessable_trials": assessed,
            "unknown_trials": unknown, "planned_trials": total,
            "frequency_among_assessable": observed / assessed if assessed else None,
            "wilson_95_interval_among_assessable": wilson(observed, assessed),
            "planned_cohort_missingness_bounds": [observed / total, (observed + unknown) / total],
            "definition": "four physical deliveries, zero claims, done=3 and assigned=1 in both terminal audit reads",
        },
        "physical_delivery_accounting_event": {
            "observed": physical_observed, "assessable_trials": physical_assessed,
            "unknown_trials": physical_unknown, "planned_trials": total,
            "frequency_among_assessable":
                physical_observed / physical_assessed if physical_assessed else None,
            "wilson_95_interval_among_assessable":
                wilson(physical_observed, physical_assessed),
            "planned_cohort_missingness_bounds":
                [physical_observed / total, (physical_observed + physical_unknown) / total],
            "definition": "four physical deliveries, zero claims, done<4 and assigned>0 with identical terminal task counters",
            "assessment": "complete observation window; invalid, changing, or impossible four-job task counters are unknown",
            "protocol": "additional prospective event; original three-of-four definition and denominator unchanged",
        },
        "limits": {
            "original_reliability_issue_resolved": False,
            "fixed_seed_pilot": True,
            "independent_units": "fresh server processes and world saves; citizens are not replicates",
            "terminal_reads_are_atomic": False,
            "interval_assumption": "independent comparable trials; fixed seeds do not establish population representativeness",
            "causal_communication_benefit_measured": False,
            "legacy_fixture_receipt_seed_is_world_provenance": False,
        },
    }
    if not result["prospective_plans"]["all_required_plans_verified"]:
        context["errors"].append("prospective plans are missing, invalid, duplicated, or do not match trusted context")
    identity_mismatches = sorted({error for trial in normalized for error in trial["errors"]
                                  if "requested context" in error or "requested commit" in error
                                  or "differs from prospective plan" in error
                                  or "prospective plan" in error and "bound" in error})
    context["errors"].extend(identity_mismatches)
    if errors:
        context["errors"].append("cohort provenance is ambiguous; inspect cohort_errors and invalid_or_duplicate_artifacts")
    if context["errors"] and context["status"] == "VERIFIED_EXPECTATIONS":
        context["status"] = "UNVERIFIED_EVIDENCE"
    result["acceptance_passed"] = (
        context["status"] == "VERIFIED_EXPECTATIONS"
        and result["all_trials_passed"]
        and result["prospective_plans"]["all_required_plans_verified"]
        and result["post_window_motor_diagnostics"]["all_required_worlds_verified"])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-commit")
    parser.add_argument("--expected-run-id",
                        help="Trusted current workflow run; never infer it from downloaded records")
    parser.add_argument("--expected-run-attempt",
                        help="Trusted current workflow attempt; consistent older attempts are rejected")
    parser.add_argument("--require-motor-diagnostics", action="store_true",
                        help="Trusted workflow requirement; artifact flags cannot disable this gate")
    parser.add_argument("--require-prospective-plans", action="store_true",
                        help="Require declarations retained before build setup for every planned world")
    args = parser.parse_args()
    records = []
    plans = []
    artifact_sources = {"plan": [], "result": []}
    for path in sorted(args.directory.rglob("trial-plan.json")):
        relative_path = path.relative_to(args.directory).as_posix()
        artifact_sources["plan"].append({"input_index": len(plans), "path": relative_path})
        try:
            document = artifact_json(path.read_text())
            if not isinstance(document, dict):
                raise ValueError("prospective plan is not an object")
            plans.append(document)
        except (OSError, ValueError) as error:
            plans.append({"trial_id": "UNREADABLE " + relative_path + ": " + str(error)})
    for path in sorted(args.directory.rglob("trial-result.json")):
        relative_path = path.relative_to(args.directory).as_posix()
        artifact_sources["result"].append({"input_index": len(records), "path": relative_path})
        try:
            record = artifact_json(path.read_text())
            if result_shape_errors(record):
                records.append(record)
                continue
            if record.get("observation_window_completed") is True or record.get("status") == "PASS":
                artifact_errors = []
                for name, key in (("rcon.log", "rcon_log_sha256"),
                                  ("forge-server.log", "server_log_sha256")):
                    try:
                        actual = hashlib.sha256((path.parent / name).read_bytes()).hexdigest()
                        if actual != record.get(key):
                            artifact_errors.append("retained log hash mismatch: " + name)
                    except OSError:
                        artifact_errors.append("retained log missing: " + name)
                world = record.get("world", {})
                if not isinstance(world, dict):
                    world = {}
                for name, key in (("level.dat", "level_dat_sha256"),
                                  ("hearthbound_world_identity_v1.dat", "world_identity_sha256")):
                    try:
                        actual = hashlib.sha256((path.parent / "world-metadata" / name).read_bytes()).hexdigest()
                        if actual != world.get(key):
                            artifact_errors.append("retained world metadata hash mismatch: " + name)
                    except OSError:
                        artifact_errors.append("retained world metadata missing: " + name)
                record["artifact_validation_errors"] = artifact_errors
            record["verified_motor_diagnostics"] = motor_diagnostics.inspect_artifact(
                path.parent, record, required=args.require_motor_diagnostics)
            records.append(record)
        except (OSError, ValueError) as error:
            # A corrupt additional artifact could hide a duplicate trial.
            # Preserve it as a cohort error and invalidate pooled estimation.
            records.append({"trial_id": "UNREADABLE " + relative_path + ": " + str(error)})
    plans_required = args.require_prospective_plans or bool(plans) or any(
        isinstance(record, dict) and record.get("prospective_plan_required") is True
        for record in records)
    expected_protocol = protocol_hash(Path(__file__).resolve().parents[1]) if plans_required else None
    result = summarize(records, expected_commit=args.expected_commit,
                       require_motor_diagnostics=args.require_motor_diagnostics,
                       prospective_plans=plans, require_prospective_plans=plans_required,
                       expected_protocol=expected_protocol,
                       expected_run_id=args.expected_run_id,
                       expected_run_attempt=args.expected_run_attempt)
    # Collected by the loader, outside the artifact payload. Filenames locate
    # evidence only; they never supply a missing or malformed trial identity.
    result["artifact_sources"] = artifact_sources
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["acceptance_passed"] else 1)


if __name__ == "__main__":
    main()
