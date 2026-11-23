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

TRIAL_SCHEMA = "hearthbound.colony-reliability-trial.v1"
SUMMARY_SCHEMA = "hearthbound.colony-reliability-summary.v1"
PLAN = tuple({"trial_id": f"world-{i:02d}", "seed": 43100 + i}
             for i in range(1, 6))
SHA = re.compile(r"[0-9a-f]{40}")
HASH = re.compile(r"[0-9a-f]{64}")
TERMINAL_STATUSES = {
    "PASS", "ACCOUNTING_THREE_OF_FOUR", "TASK_ACCOUNTING_MISMATCH",
    "FIXTURE_ASSERTION_FAILURE", "INFRASTRUCTURE_FAILURE", "INVALID_EVIDENCE",
}


def protocol_hash(repo):
    """Pin the actual fixture, runner, aggregation rules, and cohort workflow."""
    names = (
        "scripts/rcon_civilization_four_citizens.py",
        "scripts/rcon_two_citizen_haul_acceptance.py",
        "scripts/run_colony_reliability_trial.py",
        "scripts/summarize_colony_reliability.py",
        ".github/workflows/real-colony-reliability.yml",
    )
    digest = hashlib.sha256()
    for name in names:
        digest.update(name.encode() + b"\0")
        digest.update((Path(repo) / name).read_bytes() + b"\0")
    return digest.hexdigest()


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


def result_errors(record, expected, expected_commit=None):
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


def summarize(records, plan=PLAN, expected_commit=None):
    by_id = {}
    errors = []
    expected_ids = {item["trial_id"] for item in plan}
    for record in records:
        trial_id = record.get("trial_id")
        if trial_id not in expected_ids:
            errors.append("unexpected trial: " + str(trial_id))
        elif trial_id in by_id:
            errors.append("duplicate trial result: " + trial_id)
        else:
            by_id[trial_id] = record
    normalized = []
    world_ids = set()
    commits, protocols = set(), set()
    for item in plan:
        record = by_id.get(item["trial_id"])
        if record is None:
            normalized.append({**item, "status": "MISSING_RESULT",
                               "accounting_event_observed": None,
                               "physical_delivery_accounting_event_observed": None,
                               "errors": ["no artifact for planned trial"]})
            continue
        invalid = result_errors(record, item, expected_commit)
        world = record.get("world", {})
        world_id = world.get("world_uuid") if isinstance(world, dict) else None
        if world_id:
            canonical = str(world_id).lower()
            if canonical in world_ids:
                invalid.append("persisted world UUID reused")
            world_ids.add(canonical)
        if record.get("source_commit"):
            commits.add(record["source_commit"])
        if record.get("protocol_sha256"):
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
        })
    if len(commits) > 1:
        errors.append("mixed tested commits")
    if len(protocols) > 1:
        errors.append("mixed protocols")
    # A duplicate, unexpected record, or mixed cohort invalidates the pooled
    # estimate instead of quietly dropping evidence until the number improves.
    if errors:
        for trial in normalized:
            trial["accounting_event_observed"] = None
            trial["physical_delivery_accounting_event_observed"] = None
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
    return {
        "schema": SUMMARY_SCHEMA,
        "planned_trials": total,
        "received_unique_trials": len(by_id),
        "statuses": dict(sorted(count.items())),
        "terminal_diagnostic_patterns": dict(sorted(diagnostic_counts.items())),
        "all_trials_passed": not errors and count["PASS"] == total,
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-commit")
    args = parser.parse_args()
    records = []
    for path in sorted(args.directory.rglob("trial-result.json")):
        try:
            record = json.loads(path.read_text())
            if not isinstance(record, dict):
                raise ValueError("result is not an object")
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
            records.append(record)
        except (OSError, ValueError) as error:
            # A corrupt additional artifact could hide a duplicate trial.
            # Preserve it as a cohort error and invalidate pooled estimation.
            records.append({"trial_id": "UNREADABLE " + str(path) + ": " + str(error)})
    result = summarize(records, expected_commit=args.expected_commit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result["all_trials_passed"] else 1)


if __name__ == "__main__":
    main()
