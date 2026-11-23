#!/usr/bin/env python3
"""Run exactly one predeclared arm in a fresh disposable Forge JVM/world."""
import argparse
import contextlib
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time
import traceback

from private_communication_protocol import SCHEMA, plan_document, write_plan
from rcon_private_communication_trial import (
    actor_witness, communication_snapshot, connection, inventories, pages,
    run_trial, runtime,
)
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
        "schema": "hearthbound.private-communication-evidence-digests.v1", "files": files})


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


def run(repo, trial_id, output, boot_timeout=720):
    planned_path = output / "planned-trial.json"
    output.mkdir(parents=True, exist_ok=True)
    if (output / "trial-result.json").exists():
        raise ValueError("Refusing to overwrite or behaviorally rerun an existing trial")
    planned = plan_document(repo, trial_id)
    if planned_path.exists():
        if json.loads(planned_path.read_text()) != planned:
            raise ValueError("Predeclared plan changed before execution")
    else:
        write_plan(repo, trial_id, planned_path)
    result = {"schema": SCHEMA, **{key: planned[key] for key in (
        "trial_id", "pair_id", "seed", "arm", "policy_seed", "source_commit", "source_tree",
        "protocol_sha256", "matched_initial_manifest_sha256")},
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "status": "STARTING", "phase": "PREFLIGHT", "fresh_world_directory": False,
        "behavioral_retries": 0, "planned_worlds": 6, "planned_pairs": 3,
        "protocol_valid": False, "world": None, "fixture": {},
        "error_type": None, "error": None,
        "communication_win_required": False, "causal_benefit_established": False,
        "learned_collaboration": False, "reward_authorized": False,
    }
    result_path = output / "trial-result.json"
    write_result(result_path, result)
    run_dir = repo / "run"
    level_name = "private-communication-" + trial_id
    world_dir = run_dir / level_name
    server_log, rcon_log = output / "forge-server.log", output / "rcon.log"
    process, ready, stopped = None, False, False
    password = secrets.token_hex(24)
    try:
        expected = os.environ.get("HEARTHBOUND_EXPECTED_COMMIT")
        if expected and planned["source_commit"] != expected:
            raise ValueError("Checkout differs from requested head revision")
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
        result.update(status="RUNNING", phase="BOOT")
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
            result["phase"] = "FIXTURE"
            write_result(result_path, result)
            with rcon_log.open("w", buffering=1) as log, contextlib.redirect_stdout(log):
                with connection(password) as rcon:
                    try:
                        run_trial(rcon, planned["seed"], planned["arm"], result["fixture"])
                        result.update(status="VALID_OBSERVATION", protocol_valid=True)
                    except Exception as error:
                        result.update(status="INVALID_OBSERVATION", error_type=type(error).__name__, error=str(error))
                        traceback.print_exc(file=log)
                        capture_diagnostics(rcon, result["fixture"])
                    write_result(result_path, result)
                    result["phase"] = "CLEAN_STOP"
                    rcon.require("save-all flush", "Saved the game")
                    try:
                        rcon.run("stop")
                    except (ConnectionError, OSError):
                        pass  # The server may close before the read-only delimiter.
            stop_process(process)
            stopped = process.returncode == 0
            process = None
        result["clean_server_exit"] = stopped
        if not stopped:
            raise RuntimeError("Forge did not exit cleanly after final evidence save")
        result["world"] = world_evidence(world_dir, level_name, planned["seed"])
        metadata = output / "world-metadata"
        metadata.mkdir(exist_ok=False)
        for source, target in ((world_dir / "level.dat", "level.dat"),
                               (world_dir / "data/hearthbound_world_identity_v1.dat", "hearthbound_world_identity_v1.dat"),
                               (world_dir / "data/hearthbound_citizen_communication_v1.dat", "hearthbound_citizen_communication_v1.dat")):
            if source.exists():
                shutil.copyfile(source, metadata / target)
        if result["fixture"].get("final", {}).get("world") != result["world"]["world_uuid"]:
            raise ValueError("Runtime world UUID differs from independently saved world identity")
        result["phase"] = "FINISHED"
    except Exception as error:
        result["status"] = "INFRASTRUCTURE_FAILURE" if not ready else "EVIDENCE_FAILURE"
        result["protocol_valid"] = False
        result["runner_error"] = type(error).__name__ + ": " + str(error)
        if result["error_type"] is None:
            result["error_type"], result["error"] = type(error).__name__, str(error)
    finally:
        if process is not None:
            try:
                with rcon_log.open("a") as log, contextlib.redirect_stdout(log):
                    with connection(password) as rcon:
                        rcon.run("save-all flush")
                        rcon.run("stop")
            except Exception:
                pass
            stop_process(process)
        for name, path in (("server_log_sha256", server_log), ("rcon_log_sha256", rcon_log)):
            if path.exists():
                result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_result(result_path, result)
        evidence_ledger(output)
    print("PRIVATE_COMMUNICATION_TRIAL " + json.dumps({
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
