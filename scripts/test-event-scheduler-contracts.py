#!/usr/bin/env python3
"""Run C14 contracts once, preserving evidence even on failure; never boot Forge."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def read_command(command, root):
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    return {"exit_code": result.returncode, "output": (result.stdout + result.stderr).strip()}


def hashes(paths, root):
    return {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in paths if path.is_file()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", type=Path,
                        help="Write a manifest and per-stage logs to a new or empty directory")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    subject = read_command(["git", "rev-parse", "HEAD"], root)
    dirty = read_command(["git", "status", "--porcelain"], root)
    destination = args.evidence_dir.resolve() if args.evidence_dir else None
    if destination:
        if destination.exists() and any(destination.iterdir()):
            parser.error("evidence directory must be empty; do not mix different runs")
        destination.mkdir(parents=True, exist_ok=True)
    java = shutil.which("java")
    javac = shutil.which("javac")
    sources = sorted((root / "src/main/java/dev/hearthbound/experiment").glob("*.java"))
    sources += sorted((root / "src/test/java/dev/hearthbound/experiment").glob("*.java"))
    tracked_inputs = sources + [root / "scripts" / name for name in (
        "event_scheduler.py", "test_event_scheduler.py", "test_event_scheduler_parity.py",
        "test-event-scheduler-contracts.py")]
    tracked_inputs += [root / "docs/C14_EVENT_SCHEDULER_CONTRACT.md"]
    fixtures = sorted((root / "tests/fixtures/event_scheduler").glob("*"))
    initial_hashes = hashes(tracked_inputs + fixtures, root)
    manifest = {
        "schema_version": 1, "ticket": "C14-01", "started_at": utc_now(), "status": "running",
        "source_git_sha": subject["output"] if subject["exit_code"] == 0 else None,
        "working_tree_dirty_at_start": bool(dirty["output"]) if dirty["exit_code"] == 0 else None,
        "python_version": sys.version, "java_version": read_command([java, "-version"], root) if java else None,
        "compiler": javac or "java --module jdk.compiler/com.sun.tools.javac.Main",
        "compile_release": 17, "source_sha256": hashes(tracked_inputs, root),
        "fixture_sha256": hashes(fixtures, root), "forge_executed": False,
        "native_physical_effects_tested": False, "learned_adaptation_tested": False,
        "stages": [{"name": name, "status": "not_run", "exit_code": None}
                   for name in ("compile_java17", "java_contracts", "python_and_cross_language_contracts")],
    }

    def save():
        if destination:
            (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    def stage(index, command, env=None):
        record = manifest["stages"][index]
        record.update(command=command, started_at=utc_now(), status="running")
        save()
        started = time.monotonic()
        result = subprocess.run(command, cwd=root, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True)
        record.update(exit_code=result.returncode, finished_at=utc_now(),
                      duration_seconds=round(time.monotonic() - started, 6),
                      status="passed" if result.returncode == 0 else "failed")
        if destination:
            filename = f"{index + 1:02d}-{record['name']}.log"
            (destination / filename).write_text(result.stdout)
            record["log_file"] = filename
        print(result.stdout, end="", flush=True)
        save()
        return result.returncode

    save()
    exit_code = 1
    try:
        if not java or not sources:
            manifest["error"] = "JDK 17+ and event scheduler Java sources are required"
            print(manifest["error"], file=sys.stderr)
            return exit_code
        missing = [str(path.relative_to(root)) for path in tracked_inputs if not path.is_file()]
        if missing or not fixtures:
            manifest["error"] = f"Required scheduler inputs are missing: {missing or ['event fixtures']}"
            print(manifest["error"], file=sys.stderr)
            return exit_code
        compiler = [javac] if javac else [java, "--module", "jdk.compiler/com.sun.tools.javac.Main"]
        with tempfile.TemporaryDirectory(prefix="hearthbound-events-") as output:
            commands = [
                compiler + ["--release", "17", "-encoding", "UTF-8", "-d", output] + [str(p) for p in sources],
                [java, "-ea", "-cp", output, "dev.hearthbound.experiment.EventSchedulerTest"],
                [sys.executable, "-m", "unittest", "discover", "-s", "scripts",
                 "-p", "test_event_scheduler*.py", "-v"],
            ]
            env = dict(os.environ, HEARTHBOUND_EVENT_JAVA_CLASSPATH=output)
            for index, command in enumerate(commands):
                exit_code = stage(index, command, env)
                if exit_code:
                    return exit_code
        if initial_hashes != hashes(tracked_inputs + fixtures, root):
            manifest["error"] = "Source or fixture changed during this run; evidence is not a stable validation"
            exit_code = 1
            print(manifest["error"], file=sys.stderr)
            return exit_code
        print("PASS event scheduler Python, Java, and cross-language contracts; Forge not executed")
        return 0
    except Exception as error:
        exit_code = 1
        manifest["error"] = f"{type(error).__name__}: {error}"
        print(manifest["error"], file=sys.stderr)
        return 1
    finally:
        passed = exit_code == 0 and all(s["status"] == "passed" for s in manifest["stages"])
        manifest.update(finished_at=utc_now(), status="passed" if passed else "failed",
                        source_changed_during_run=initial_hashes != hashes(tracked_inputs + fixtures, root))
        save()


if __name__ == "__main__":
    raise SystemExit(main())
