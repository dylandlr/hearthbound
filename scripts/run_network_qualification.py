#!/usr/bin/env python3
"""Run exactly one predeclared arm in a fresh disposable Forge JVM/world."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import time
import traceback

from network_qualification_protocol import SCHEMA, LEDGER_SCHEMA, context, digest, load_json, plan_document
from run_forge_build_preflight import BUILD_INPUTS, environment_errors
from datetime import datetime, timezone
from rcon_network_qualification import (
    actor_witness, communication_snapshot, connection, inventories, pages,
    run_trial, runtime,
)
from rcon_private_communication_trial import require
from run_colony_reliability_trial import READY, stop_process, world_evidence


def write_result(path, result):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    temporary.replace(path)


def evidence_ledger(output):
    files = {}
    for path in sorted(output.rglob("*")):
        if path.is_file() and path.name != "evidence-sha256.json":
            files[str(path.relative_to(output))] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_result(output / "evidence-sha256.json", {
        "schema": LEDGER_SCHEMA, "files": files})


def advance_phase(result, phase):
    """Preserve the original failure phase while cleanup continues."""
    result["last_runner_phase"] = phase
    if result["error_type"] is None:
        result["phase"] = phase


def record_error(result, status, phase, error):
    entry = {"status": status, "phase": phase,
             "error_type": type(error).__name__, "error": str(error)}
    result["protocol_valid"] = False
    if result["error_type"] is None:
        result.update(entry)
        result["failure_phase"] = phase
    else:
        result.setdefault("secondary_errors", []).append(entry)


def capture_world_metadata(result, world_dir, level_name, seed, output):
    """Saved world evidence remains useful even when setup never reached start."""
    metadata = output / "world-metadata"
    metadata.mkdir(exist_ok=False)
    for source, target in ((world_dir / "level.dat", "level.dat"),
                           (world_dir / "data/hearthbound_world_identity_v1.dat", "hearthbound_world_identity_v1.dat"),
                           (world_dir / "data/hearthbound_citizen_communication_v1.dat", "hearthbound_citizen_communication_v1.dat")):
        if source.exists():
            shutil.copyfile(source, metadata / target)
    result["world"] = world_evidence(world_dir, level_name, seed)
    final = result["fixture"].get("final")
    if final is not None and final.get("world") != result["world"]["world_uuid"]:
        raise ValueError("Runtime world UUID differs from independently saved world identity")


def capture_diagnostics(rcon, data):
    diagnostics = {"partial": True, "not_promoted_to_valid_observation": True}
    readers = {"runtime": lambda: runtime(rcon), "actors": lambda: pages(rcon, "actors"),
               "records": lambda: pages(rcon, "records"),
               "communication": lambda: communication_snapshot(rcon),
               "inventories": lambda: inventories(rcon)}
    for name, reader in readers.items():
        try:
            diagnostics[name] = reader()
        except Exception as error:
            diagnostics[name + "_error"] = type(error).__name__ + ": " + str(error)
    for actor in diagnostics.get("actors", []):
        try:
            diagnostics.setdefault("native_actors", []).append(actor_witness(rcon, actor["citizen"]))
        except Exception as error:
            diagnostics.setdefault("native_actor_errors", []).append(type(error).__name__ + ": " + str(error))
    data["diagnostics"] = diagnostics


def validate_build_record(repo, planned, directory):
    preflight = load_json(directory / "preflight.json")
    require(preflight["schema"] == "hearthbound-forge-build-preflight-v1"
            and preflight["status"] == "PASS" and preflight["source_commit"] == planned["source_commit"]
            and preflight["expected_source_commit"] == planned["source_commit"]
            and preflight["build_attempts"] == 1 and preflight["automatic_retries"] == 0
            and preflight["forced_fallback"] is False and preflight["build_exit_code"] == preflight["exit_code"] == 0
            and preflight["log_finalized"] is True and not preflight["errors"] and not preflight["evidence_errors"],
            "Qualification requires one complete successful source-bound ordinary build")
    require(preflight["build_input_sha256"] == {name: hashlib.sha256((repo / name).read_bytes()).hexdigest()
                                              for name in BUILD_INPUTS}, "Qualification build inputs changed")
    require(environment_errors(preflight["resolved_build_environment"]) == [], "Invalid resolved build dependencies")
    require(load_json(directory / "build-environment.json") == preflight["resolved_build_environment"],
            "Resolved environment export mismatch")
    log = (directory / "preflight.log").read_bytes()
    require(hashlib.sha256(log).hexdigest() == preflight["log_sha256"], "Build log digest mismatch")
    text = log.decode("utf-8", errors="strict")
    require(all(re.search(r"^> Task :" + task + r"\s*$", text, re.M) for task in ("compileJava", "compileTestJava"))
            and "BUILD SUCCESSFUL" in text, "Actual production/test compilation not evidenced")
    declared = datetime.fromisoformat(planned["declaration_utc"])
    started, finished = (datetime.fromisoformat(preflight[key].replace("Z", "+00:00"))
                         for key in ("started_at", "finished_at"))
    require(declared <= started <= finished, "Qualification declaration did not precede dependency setup")
    return {"status": "PASS", "build_attempts": 1, "automatic_retries": 0,
            "log_sha256": preflight["log_sha256"], "resolved_environment": preflight["resolved_build_environment"],
            "source_inputs_verified": True, "declaration_precedes_setup": True}


def capture_build(repo, output, planned):
    execution = planned["execution_context"]
    require(execution == context() and execution["run_attempt"] == "1"
            and all(isinstance(execution[key], str) and execution[key] for key in ("workflow", "run_id")),
            "Qualification requires its predeclared first workflow attempt")
    source = repo / "network-qualification-build"
    destination = output / "build-evidence"
    destination.mkdir(exist_ok=False)
    for name in ("preflight.json", "build-environment.json", "gradle-version.log", "java-version.log"):
        shutil.copyfile(source / name, destination / name)
    shutil.copyfile(repo / "network-qualification-preflight.log", destination / "preflight.log")
    return validate_build_record(repo, planned, destination)


def run(repo, trial_id, output, boot_timeout=720):
    planned_path = output / "planned-trial.json"
    output.mkdir(parents=True, exist_ok=True)
    if (output / "trial-result.json").exists():
        raise ValueError("Refusing to overwrite or behaviorally rerun an existing trial")
    if not planned_path.exists():
        raise ValueError("Qualification plan must exist before dependency setup")
    saved_plan = load_json(planned_path)
    planned = plan_document(repo, trial_id, saved_plan["declaration_utc"])
    if saved_plan != planned:
        raise ValueError("Predeclared plan changed before execution")
    reservation = {"schema": "hearthbound.network-qualification-attempt.v1",
                   "trial_id": trial_id, "source_commit": planned["source_commit"],
                   "plan_sha256": digest(planned), "execution_context": context(),
                   "reserved_utc": datetime.now(timezone.utc).isoformat(), "attempt": 1}
    with (output / "world-attempt.json").open("x") as handle:
        handle.write(json.dumps(reservation, indent=2, sort_keys=True) + "\n")
    result = {"schema": SCHEMA, **{key: planned[key] for key in (
        "trial_id", "block_id", "seed", "arm", "policy_seed", "source_commit", "source_tree",
        "protocol_sha256", "initial_manifest_sha256")},
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "status": "STARTING", "phase": "PREFLIGHT", "fresh_world_directory": False,
        "behavioral_retries": 0, "planned_worlds": 6, "qualification_only": True, "expanded_study_worlds": 0,
        "protocol_valid": False, "world": None, "fixture": {},
        "error_type": None, "error": None, "secondary_errors": [],
        "communication_win_required": False, "causal_benefit_established": False,
        "learned_collaboration": False, "reward_authorized": False, "execution_context": context(),
    }
    result_path = output / "trial-result.json"
    write_result(result_path, result)
    run_dir = repo / "run"
    level_name = "network-qualification-" + trial_id
    world_dir = run_dir / level_name
    server_log, rcon_log = output / "forge-server.log", output / "rcon.log"
    process, ready = None, False
    result["last_runner_phase"] = "PREFLIGHT"
    password = secrets.token_hex(24)
    try:
        expected = os.environ.get("HEARTHBOUND_EXPECTED_COMMIT")
        if expected and planned["source_commit"] != expected:
            raise ValueError("Checkout differs from requested head revision")
        result["build_evidence"] = capture_build(repo, output, planned)
        run_dir.mkdir(exist_ok=True)
        if world_dir.exists():
            raise ValueError("Refusing to reuse an existing world directory")
        result["fresh_world_directory"] = True
        with (run_dir / "server.properties").open("x") as properties:
            properties.write("server-ip=127.0.0.1\nonline-mode=false\n"
                             f"level-name={level_name}\nlevel-seed={planned['seed']}\nmax-players=2\n"
                             "enable-rcon=true\nrcon.port=25575\n"
                             f"rcon.password={password}\n")
        eula = run_dir / "eula.txt"
        if eula.exists():
            if "eula=true" not in eula.read_text():
                raise ValueError("Existing EULA does not enable disposable server")
        else:
            eula.write_text("eula=true\n")
        result["status"] = "RUNNING"
        advance_phase(result, "BOOT")
        write_result(result_path, result)
        with server_log.open("w") as log:
            process = subprocess.Popen(["gradle", "--no-daemon", "runServer"], cwd=repo,
                                       stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + boot_timeout
            while True:
                output_text = server_log.read_text(errors="replace")
                if READY.search(output_text):
                    if "Hearthbound bootstrap loaded." not in output_text:
                        raise RuntimeError("Forge booted without Hearthbound")
                    ready = True
                    break
                if process.poll() is not None:
                    raise RuntimeError("Forge exited before server readiness")
                if time.monotonic() >= deadline:
                    raise TimeoutError("Forge readiness deadline exceeded")
                time.sleep(2)
            advance_phase(result, "FIXTURE")
            write_result(result_path, result)
            with rcon_log.open("w", buffering=1) as log, contextlib.redirect_stdout(log):
                with connection(password) as rcon:
                    try:
                        run_trial(rcon, planned["seed"], planned["arm"], result["fixture"])
                        result.update(status="VALID_OBSERVATION", protocol_valid=True)
                    except Exception as error:
                        record_error(result, "INVALID_OBSERVATION", "FIXTURE", error)
                        traceback.print_exc(file=log)
                        capture_diagnostics(rcon, result["fixture"])
                    write_result(result_path, result)
                    advance_phase(result, "CLEAN_STOP")
                    try:
                        rcon.require("save-all flush", "Saved the game")
                    except Exception as error:
                        record_error(result, "EVIDENCE_FAILURE", "CLEAN_STOP", error)
                    try:
                        rcon.stop_server()
                    except (ConnectionError, OSError):
                        pass  # Normal shutdown may close before its acknowledgement.
            stop_process(process)
            result["server_exit_code"] = process.returncode
            result["clean_server_exit"] = process.returncode == 0
            process = None
        if not result["clean_server_exit"]:
            record_error(result, "EVIDENCE_FAILURE", "CLEAN_STOP",
                         RuntimeError("Forge did not exit cleanly after final evidence save"))
    except Exception as error:
        record_error(result, ("NOT_RUN_BEFORE_RUNTIME" if result["last_runner_phase"] == "PREFLIGHT"
                              else "INFRASTRUCTURE_FAILURE" if not ready else "EVIDENCE_FAILURE"),
                     result["last_runner_phase"], error)
    finally:
        if process is not None:
            advance_phase(result, "CLEAN_STOP")
            if process.poll() is None:
                try:
                    with rcon_log.open("a") as log, contextlib.redirect_stdout(log):
                        with connection(password) as rcon:
                            rcon.require("save-all flush", "Saved the game")
                            try:
                                rcon.stop_server()
                            except (ConnectionError, OSError):
                                pass
                except Exception as error:
                    record_error(result, "EVIDENCE_FAILURE", "CLEAN_STOP", error)
            stop_process(process)
            result["server_exit_code"] = process.returncode
            result["clean_server_exit"] = process.returncode == 0
            if not result["clean_server_exit"]:
                record_error(result, "EVIDENCE_FAILURE", "CLEAN_STOP",
                             RuntimeError("Forge did not exit cleanly after final evidence save"))
        if ready:
            advance_phase(result, "WORLD_METADATA")
            try:
                capture_world_metadata(result, world_dir, level_name, planned["seed"], output)
            except Exception as error:
                record_error(result, "EVIDENCE_FAILURE", "WORLD_METADATA", error)
        if result["error_type"] is None:
            advance_phase(result, "FINISHED")
        for name, path in (("server_log_sha256", server_log), ("rcon_log_sha256", rcon_log)):
            if path.exists():
                result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_result(result_path, result)
        evidence_ledger(output)
    print("NETWORK_QUALIFICATION_TRIAL " + json.dumps({
        key: result[key] for key in ("trial_id", "arm", "status", "protocol_valid", "error_type", "error")},
        sort_keys=True))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--boot-timeout", type=int, default=720)
    args = parser.parse_args()
    outcome = run(Path(__file__).resolve().parents[1], args.trial_id, args.output.resolve(), args.boot_timeout)
    raise SystemExit(0 if outcome["status"] == "VALID_OBSERVATION" else 1)
