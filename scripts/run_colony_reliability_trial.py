#!/usr/bin/env python3
"""Run one predeclared reliability trial in a fresh disposable Forge world.

The runner never deletes a world or overwrites existing server.properties.
Each CI matrix job has its own checkout, JVM, world directory, and save UUID.
"""
import argparse
import contextlib
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import signal
import socket
import struct
import subprocess
import time
import traceback
from uuid import UUID

import rcon_civilization_four_citizens as fixture
import colony_motor_diagnostics as motor_diagnostics
from rcon_two_citizen_haul_acceptance import Rcon, exact, packet
from summarize_colony_reliability import (
    PLAN, PLAN_SCHEMA, TRIAL_SCHEMA, classified_status, counters, plan_errors,
    plan_hash, protocol_hash,
)

READY = re.compile(r'Done \([0-9.]+s\)! For help, type "help"')


class TraceRetainingRcon(Rcon):
    """Pass through the original fixture unchanged while retaining its trace reply."""
    def __init__(self, sock):
        super().__init__(sock)
        self.retained_decision_traces = []

    def run(self, command):
        request_id = self.next_id
        response = super().run(command)
        if command == motor_diagnostics.TRACE_COMMAND:
            # No parsing, validation, extra command, retry, or exception handling
            # belongs in the original fixture's execution window.
            self.retained_decision_traces.append({
                "command": command, "request_id": request_id, "response": response})
        return response


class NbtReader:
    """Small bounded NBT reader for saved world identity and level seed only."""
    def __init__(self, payload):
        if len(payload) > 64 * 1024 * 1024:
            raise ValueError("Oversized world metadata")
        self.payload, self.offset = payload, 0

    def take(self, size):
        if size < 0 or self.offset + size > len(self.payload):
            raise ValueError("Truncated NBT metadata")
        value = self.payload[self.offset:self.offset + size]
        self.offset += size
        return value

    def number(self, format):
        return struct.unpack(">" + format, self.take(struct.calcsize(">" + format)))[0]

    def string(self):
        return self.take(self.number("H")).decode("utf-8")

    def value(self, kind, depth=0):
        if depth > 64:
            raise ValueError("Excessive NBT nesting")
        if kind in (1, 2, 3, 4, 5, 6):
            return self.number({1: "b", 2: "h", 3: "i", 4: "q", 5: "f", 6: "d"}[kind])
        if kind == 8:
            return self.string()
        if kind in (7, 11, 12):
            count = self.number("i")
            if not 0 <= count <= 4_000_000:
                raise ValueError("Invalid NBT array size")
            self.take(count * {7: 1, 11: 4, 12: 8}[kind])
            return None
        if kind == 9:
            child, count = self.number("B"), self.number("i")
            if not 0 <= count <= 1_000_000 or child == 0 and count:
                raise ValueError("Invalid NBT list")
            return [self.value(child, depth + 1) for _ in range(count)]
        if kind == 10:
            result = {}
            while True:
                child = self.number("B")
                if child == 0:
                    return result
                name = self.string()
                if name in result:
                    raise ValueError("Duplicate NBT key")
                result[name] = self.value(child, depth + 1)
        raise ValueError("Unsupported NBT type")

    def root(self):
        if self.number("B") != 10:
            raise ValueError("NBT root is not a compound")
        self.string()
        value = self.value(10)
        if self.offset != len(self.payload):
            raise ValueError("Trailing NBT bytes")
        return value


def world_evidence(directory, level_name, seed):
    level_path = directory / "level.dat"
    identity_path = directory / "data/hearthbound_world_identity_v1.dat"
    level_bytes, identity_bytes = level_path.read_bytes(), identity_path.read_bytes()
    level = NbtReader(gzip.decompress(level_bytes)).root()
    identity = NbtReader(gzip.decompress(identity_bytes)).root()
    world_uuid = str(UUID(identity["data"]["worldUuid"]))
    generated_seed = level["Data"]["WorldGenSettings"]["seed"]
    if type(generated_seed) is not int or generated_seed != seed:
        raise ValueError("Generated world seed differs from declared seed")
    return {
        "level_name": level_name,
        "configured_seed": str(seed),
        "generated_seed": generated_seed,
        "world_uuid": world_uuid,
        "level_dat_sha256": hashlib.sha256(level_bytes).hexdigest(),
        "world_identity_sha256": hashlib.sha256(identity_bytes).hexdigest(),
        "origin": "PERSISTED_FORGE_LEVEL_DAT_AND_HEARTHBOUND_SAVEDDATA",
    }


@contextlib.contextmanager
def connection(password):
    with socket.create_connection(("127.0.0.1", 25575), timeout=15) as sock:
        sock.settimeout(20)
        sock.sendall(packet(1, 3, password))
        for _ in range(4):
            size = struct.unpack("<i", exact(sock, 4))[0]
            if not 10 <= size <= 1_000_000:
                raise ValueError("Invalid RCON authentication frame")
            frame = exact(sock, size)
            request, kind = struct.unpack("<ii", frame[:8])
            if request == -1:
                raise ValueError("RCON authentication rejected")
            if request == 1 and kind == 2:
                yield TraceRetainingRcon(sock)
                return
        raise ValueError("RCON authentication response missing")


def terminal_snapshot(rcon):
    """Read-only probes; the two audits expose reconciliation during probing."""
    before = rcon.run("hearthbound-colony audit")
    destination = rcon.run(
        'execute if data block 16 100 1 Items[{id:"minecraft:wheat",Count:4b}]')
    sources = [rcon.run(
        f'execute unless data block {x} 100 1 Items[{{id:"minecraft:wheat"}}]')
        for x in fixture.SOURCES]
    claims = rcon.run("hearthboundclaims count")
    reconciliation = rcon.run("hearthbound-colony physical-reconciliation-audit")
    history = rcon.run("hearthbound-colony history-audit")
    after = rcon.run("hearthbound-colony audit")
    claims_match = re.search(r"Active source claims in this dimension: (\d+)", claims)
    return {
        "audit_before": counters(before, "COLONY_V1"),
        "audit_after": counters(after, "COLONY_V1"),
        "destination_has_exact_four_wheat": "test passed" in destination.lower(),
        "source_wheat_absent": ["test passed" in value.lower() for value in sources],
        "outstanding_claims": int(claims_match[1]) if claims_match else None,
        "history": counters(history, "COLONY_HISTORY_V0_5"),
        "reconciliation": reconciliation,
        "read_only": True,
        "atomic": False,
    }


def stop_process(process):
    if process is None:
        return
    try:
        process.wait(timeout=60)
        return
    except subprocess.TimeoutExpired:
        pass
    for action, timeout in ((signal.SIGTERM, 10), (signal.SIGKILL, 10)):
        try:
            os.killpg(process.pid, action)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=timeout)
            return
        except subprocess.TimeoutExpired:
            pass


def write_result(path, result):
    # Replace only the result that this invocation created in its own output dir.
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def declare(repo, trial_id, seed, output):
    """Preserve intent before compilation without creating or observing a world."""
    item = {"trial_id": trial_id, "seed": seed}
    if item not in PLAN:
        raise ValueError("Trial is not in the predeclared cohort")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    expected_head = os.environ.get("HEARTHBOUND_EXPECTED_COMMIT")
    if expected_head and expected_head != commit:
        raise ValueError("Checkout does not match the requested head commit")
    document = {
        "schema": PLAN_SCHEMA, **item,
        "source_commit": commit, "protocol_sha256": protocol_hash(repo),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "level_name": "colony-reliability-" + trial_id,
        "declaration_phase": "BEFORE_BUILD_PREFLIGHT",
        "execution_policy": "ONE_ATTEMPT_PER_PLANNED_WORLD",
        "fresh_world_required": True, "motor_diagnostics_required": True,
    }
    invalid = plan_errors(document, item, commit, document["protocol_sha256"])
    if invalid:
        raise ValueError("Invalid prospective declaration: " + "; ".join(invalid))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as destination:
        destination.write(json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return document


def run(repo, trial_id, seed, output, boot_timeout=720, plan_file=None):
    if {"trial_id": trial_id, "seed": seed} not in PLAN:
        raise ValueError("Trial is not in the predeclared cohort")
    output.mkdir(parents=True, exist_ok=False)
    result_path = output / "trial-result.json"
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    result = {
        "schema": TRIAL_SCHEMA, "trial_id": trial_id, "seed": seed,
        "source_commit": commit, "protocol_sha256": protocol_hash(repo),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "status": "RUNNING", "fixture_passed": False,
        "observation_window_completed": False, "fresh_world_directory": False,
        "world": {}, "terminal_snapshot": None,
        "error_type": None, "error": None,
        "motor_diagnostics_required": True,
        "prospective_plan_required": plan_file is not None,
        "prospective_plan_sha256": None,
        "motor_diagnostics": {"status": "NOT_REACHED"},
        "legacy_receipt_fixture_seed_is_actual_seed": False,
    }
    write_result(result_path, result)
    process = None
    password = secrets.token_hex(24)
    level_name = "colony-reliability-" + trial_id
    run_dir = repo / "run"
    world_dir = run_dir / level_name
    server_log = output / "forge-server.log"
    rcon_log = output / "rcon.log"
    try:
        expected_head = os.environ.get("HEARTHBOUND_EXPECTED_COMMIT")
        if expected_head and expected_head != commit:
            raise ValueError("Checkout does not match the requested head commit")
        if plan_file is not None:
            declaration = json.loads(plan_file.read_text())
            invalid = plan_errors(declaration, {"trial_id": trial_id, "seed": seed},
                                  commit, result["protocol_sha256"])
            if not invalid:
                for field in ("github_run_id", "github_run_attempt"):
                    if declaration[field] != result[field]:
                        invalid.append("workflow identity changed since declaration: " + field)
            if invalid:
                raise ValueError("Prospective plan cannot authorize this trial: " + "; ".join(invalid))
            result["prospective_plan_sha256"] = plan_hash(declaration)
        run_dir.mkdir(exist_ok=True)
        if world_dir.exists():
            raise ValueError("Refusing to reuse an existing world directory")
        result["fresh_world_directory"] = True
        # Exclusive creation refuses to repurpose an existing server setup.
        with (run_dir / "server.properties").open("x") as properties:
            properties.write(
                "server-ip=127.0.0.1\nonline-mode=false\n"
                f"level-name={level_name}\nlevel-seed={seed}\nmax-players=2\n"
                "enable-rcon=true\nrcon.port=25575\n"
                f"rcon.password={password}\n")
        eula = run_dir / "eula.txt"
        if eula.exists():
            if "eula=true" not in eula.read_text():
                raise ValueError("Existing EULA file does not enable disposable server")
        else:
            eula.write_text("eula=true\n")
        write_result(result_path, result)
        with server_log.open("w") as log:
            process = subprocess.Popen(
                ["gradle", "--no-daemon", "runServer"], cwd=repo,
                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            deadline = time.monotonic() + boot_timeout
            while True:
                text = server_log.read_text(errors="replace")
                if READY.search(text):
                    if "Hearthbound bootstrap loaded." not in text:
                        raise RuntimeError("Forge booted without Hearthbound")
                    break
                if process.poll() is not None:
                    raise RuntimeError("Forge process exited before readiness")
                if time.monotonic() >= deadline:
                    raise TimeoutError("Forge server readiness deadline exceeded")
                time.sleep(2)
            with rcon_log.open("w", buffering=1) as log, contextlib.redirect_stdout(log):
                with connection(password) as rcon:
                    try:
                        fixture.run_trial(rcon)
                        result["fixture_passed"] = True
                        result["observation_window_completed"] = True
                    except Exception as error:
                        result["error_type"] = type(error).__name__
                        result["error"] = str(error)
                        result["observation_window_completed"] = (
                            isinstance(error, AssertionError)
                            and str(error).startswith("Four independently observed jobs did not complete:"))
                        traceback.print_exc(file=log)
                    try:
                        result["terminal_snapshot"] = terminal_snapshot(rcon)
                    except Exception as error:
                        result["diagnostic_error"] = type(error).__name__ + ": " + str(error)
                    # Freeze the original scoring evidence before the additional
                    # read-only observations. Natural later completion is diagnostic
                    # history and never changes this fixture's result or deadline.
                    if result["observation_window_completed"] and result["terminal_snapshot"] is not None:
                        try:
                            report = motor_diagnostics.capture(
                                rcon, result["terminal_snapshot"],
                                retained_traces=rcon.retained_decision_traces)
                            payload = (json.dumps(report, indent=2, sort_keys=True,
                                                  allow_nan=False) + "\n").encode()
                            (output / motor_diagnostics.FILENAME).write_bytes(payload)
                            result["motor_diagnostics"] = {
                                "status": report["status"], "file": motor_diagnostics.FILENAME,
                                "sha256": hashlib.sha256(payload).hexdigest(),
                                "error": "; ".join(report["errors"]) or None,
                            }
                        except Exception as error:
                            result["motor_diagnostics"] = {
                                "status": "CAPTURE_ERROR", "error": type(error).__name__ + ": " + str(error)}
                    else:
                        result["motor_diagnostics"] = {"status": "NO_COMPLETED_OBSERVATION_WINDOW"}
                    # Disable only after terminal diagnostics, without task repair.
                    rcon.run("hearthbound-colony disable")
                    rcon.run("save-all flush")
                    try:
                        rcon.run("stop")
                    except (ConnectionError, OSError):
                        pass  # Normal shutdown may close before the reply arrives.
            stop_process(process)
            process = None
        result["world"] = world_evidence(world_dir, level_name, seed)
        metadata = output / "world-metadata"
        metadata.mkdir()
        shutil.copyfile(world_dir / "level.dat", metadata / "level.dat")
        shutil.copyfile(world_dir / "data/hearthbound_world_identity_v1.dat",
                        metadata / "hearthbound_world_identity_v1.dat")
        result["status"] = classified_status(
            result["fixture_passed"], result["observation_window_completed"],
            result["error_type"], result["terminal_snapshot"])
    except Exception as error:
        result["status"] = "INFRASTRUCTURE_FAILURE"
        result["runner_error"] = type(error).__name__ + ": " + str(error)
        if result["error_type"] is None:
            result["error_type"], result["error"] = type(error).__name__, str(error)
    finally:
        if process is not None:
            # Best effort stop; never leave a child Forge process behind.
            try:
                with rcon_log.open("a") as log, contextlib.redirect_stdout(log):
                    with connection(password) as rcon:
                        rcon.run("stop")
            except Exception:
                pass
            stop_process(process)
        for name, path in (("server_log_sha256", server_log), ("rcon_log_sha256", rcon_log)):
            if path.exists():
                result[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        write_result(result_path, result)
    print("COLONY_RELIABILITY_TRIAL " + json.dumps(result, sort_keys=True))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--boot-timeout", type=int, default=720)
    parser.add_argument("--declare-only", action="store_true",
                        help="Write the prospective plan to --output without starting build or world")
    parser.add_argument("--plan-file", type=Path,
                        help="Validate the pre-build declaration before starting this world")
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    if args.declare_only:
        if args.plan_file is not None:
            parser.error("--declare-only cannot consume --plan-file")
        document = declare(repo, args.trial_id, args.seed, args.output.resolve())
        print("COLONY_RELIABILITY_PLAN " + json.dumps(document, sort_keys=True))
        return
    result = run(repo, args.trial_id, args.seed, args.output.resolve(), args.boot_timeout,
                 plan_file=args.plan_file.resolve() if args.plan_file is not None else None)
    raise SystemExit(0 if result["status"] == "PASS"
                     and result["motor_diagnostics"]["status"] == "COMPLETE" else 1)


if __name__ == "__main__":
    main()
