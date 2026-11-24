#!/usr/bin/env python3
"""One evidenced Forge build attempt. Never retry or start a Minecraft trial."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
BUILD_INPUTS = (
    "build.gradle", "settings.gradle", "gradle.properties",
    "gradle/forge-build-environment.gradle",
    "gradle/force-forge-tool-fallback.init.gradle",
    "scripts/run_forge_build_preflight.py",
)
SCHEMA = "hearthbound-forge-build-preflight-v1"
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")


class BuildCleanupError(RuntimeError):
    """Retained log bytes cannot be finalized while owned writers survive."""


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def failure_status(log, root=ROOT):
    # Only errors in this project's src tree establish a source failure. Forge's
    # generated/cache Start.java may fail after an MCP tool dependency is absent.
    root = Path(root).resolve()
    for match in re.finditer(r"(?m)^([^\r\n]+\.java):\d+:\s+error:", log):
        path = Path(match.group(1).strip())
        if not path.is_absolute():
            path = root / path
        if path.resolve().is_relative_to(root / "src"):
            return "SOURCE_COMPILATION_FAILURE"
    if re.search(r"Could not resolve|Cannot resolve external dependency|Could not find .*_mapped_|no repositories are defined|Could not download MCP Config dependency", log):
        return "DEPENDENCY_RESOLUTION_FAILURE"
    return "BUILD_FAILURE"


def mapped_policy_errors(policy):
    if not isinstance(policy, dict):
        return ["Missing mapped-version repository filter policy."]
    repositories = policy.get("external_repositories")
    if (policy.get("policy") != "exclude-mapped-versions-once-v1"
            or policy.get("version_pattern") != ".*_mapped_.*"
            or policy.get("upstream_repeated_filter_enabled") is not False
            or policy.get("generated_repositories_exempt") is not True
            or not isinstance(repositories, list) or not repositories
            or any(not isinstance(repo, dict) or not repo.get("name")
                   or type(repo.get("applications")) is not int or repo["applications"] != 1
                   for repo in repositories)):
        return ["The same mapped-version policy must be applied once per external repository with the upstream repeated callback disabled."]
    return []


def environment_errors(environment):
    if not isinstance(environment, dict) or environment.get("schema") != "hearthbound-forge-build-environment-v1":
        return ["Missing or invalid resolved build environment."]
    errors = []
    plugins = environment.get("resolved_build_plugins", [])
    expected = {("net.minecraftforge.gradle", "ForgeGradle"), ("org.spongepowered", "mixingradle")}
    if not isinstance(plugins, list) or {(p.get("group"), p.get("name")) for p in plugins if isinstance(p, dict)} != expected:
        errors.append("Both resolved ForgeGradle and MixinGradle artifacts are required.")
    elif len(plugins) != 2 or any(not p.get("resolved_version") or not HASH_RE.fullmatch(str(p.get("artifact_sha256", ""))) for p in plugins):
        errors.append("Resolved plugin versions and SHA-256 values are required.")
    for field in ("gradle_version", "java_runtime_version", "java_vendor", "configured_java_toolchain_language_version"):
        if not environment.get(field):
            errors.append(f"Missing build environment field: {field}.")
    errors += mapped_policy_errors(environment.get("mapped_repository_filter"))
    return errors


def fallback_errors(fallback):
    if not isinstance(fallback, dict) or fallback.get("schema") != "hearthbound-forge-tool-fallback-v1":
        return ["Missing or invalid forced fallback verification."]
    forced = fallback.get("forced_maven_exclusions")
    if (fallback.get("status") != "PASS" or fallback.get("repositories_restored") is not True
            or fallback.get("resolution_path") != "forgegradle_non_maven_gradle_fallback"
            or not isinstance(forced, list) or not forced
            or any(not isinstance(name, str) or not name for name in forced)
            or not HASH_RE.fullmatch(str(fallback.get("artifact_sha256", "")))):
        return ["The actual ForgeGradle fallback and repository restoration were not verified."]
    errors = mapped_policy_errors(fallback.get("mapped_repository_filter"))
    before = fallback.get("mapped_exclusions_before")
    after = fallback.get("mapped_exclusions_after")
    if (fallback.get("mapped_version_exclusions_verified") is not True
            or not isinstance(before, list) or not before or before != after
            or any(not isinstance(repo, dict) or repo.get("mapped_installer_excluded") is not True
                   for repo in before)
            or not any(repo.get("name") == "HearthboundForgeInstallerToolsFallback"
                       and repo.get("unmapped_installer_excluded") is False
                       for repo in before if isinstance(repo, dict))):
        errors.append("Actual mapped-version exclusions and fallback eligibility must be verified before and after resolution.")
    probes = [repo for repo in before if isinstance(repo, dict) and repo.get("name") in forced] if isinstance(before, list) else []
    if (fallback.get("non_target_installer_coordinate") != "net.minecraftforge:installertools:1.3.2:fatjar"
            or fallback.get("non_target_maven_eligibility_verified") is not True
            or len(probes) != len(forced) or {repo.get("name") for repo in probes} != set(forced)
            or any(repo.get("unmapped_installer_excluded") is not True
                   or repo.get("non_target_installer_excluded") is not False for repo in probes)):
        errors.append("The forced Maven filter must exclude only installer-tools 1.4.4 while keeping MCP tool 1.3.2 eligible before and after resolution.")
    return errors


def process_identity(pid):
    """Linux CI process identity without command lines or environment values."""
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        return {"state": fields[0], "parent": int(fields[1]), "group": int(fields[2]), "started": fields[19]}
    except (OSError, ValueError, IndexError):
        return None


def build_descendants(launcher_pid):
    # Gradle's single-use daemon may detach into its own process group. Record
    # descendant identities before terminating the launcher so those groups
    # cannot escape cleanup merely by being reparented.
    processes = {}
    for path in Path("/proc").glob("[0-9]*/stat"):
        pid = int(path.parent.name)
        identity = process_identity(pid)
        if identity:
            processes[pid] = identity
    owned = {launcher_pid}
    while True:
        children = {pid for pid, identity in processes.items() if identity["parent"] in owned}
        if children <= owned:
            break
        owned.update(children)
    return {pid: processes[pid] for pid in owned if pid in processes}


def signal_build(launcher_pid, descendants, requested_signal):
    signaled_groups = set()
    for pid, identity in descendants.items():
        current = process_identity(pid)
        if current is None or current["started"] != identity["started"]:
            continue  # The original child exited; never target a recycled PID.
        try:
            if current["group"] in (pid, launcher_pid):
                if current["group"] not in signaled_groups:
                    os.killpg(current["group"], requested_signal)
                    signaled_groups.add(current["group"])
            else:
                os.kill(pid, requested_signal)
        except ProcessLookupError:
            pass


def run_build(command, root, stream, timeout_seconds, termination_grace_seconds=5):
    """Stop the launcher and its process group before freezing timeout evidence."""
    process = subprocess.Popen(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                               start_new_session=True)
    try:
        return process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        descendants = build_descendants(process.pid)
        signal_build(process.pid, descendants, signal.SIGTERM)
        try:
            process.wait(timeout=termination_grace_seconds)
        except subprocess.TimeoutExpired:
            pass
        finally:
            # The launcher can exit on TERM while a child keeps writing. Kill
            # the remaining group even when wait() already reaped the launcher.
            signal_build(process.pid, descendants, signal.SIGKILL)
            try:
                process.wait(timeout=termination_grace_seconds)
            except subprocess.TimeoutExpired as error:
                raise BuildCleanupError('Timed-out build launcher did not exit after SIGKILL.') from error
            deadline = time.monotonic() + termination_grace_seconds
            while True:
                alive = [pid for pid, identity in descendants.items()
                         if (current := process_identity(pid)) is not None
                         and current["started"] == identity["started"] and current["state"] != "Z"]
                if not alive:
                    break
                if time.monotonic() >= deadline:
                    raise BuildCleanupError("Timed-out build descendants did not exit after SIGKILL.")
                time.sleep(0.01)
        raise


def run_preflight(output, log_path=None, force_fallback=False, require_empty_cache=False,
                  timeout_seconds=1200, root=ROOT):
    root = Path(root).resolve()
    output = Path(output).resolve()
    log_path = Path(log_path).resolve() if log_path else output / "gradle.log"
    protected = [output / name for name in ("preflight.json", "build-environment.json", "fallback-verification.json")]
    if log_path.exists() or any(path.exists() for path in protected):
        raise ValueError("Preflight evidence already exists; use a new output directory and log path.")
    output.mkdir(parents=True, exist_ok=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    gradle_user_home = Path(os.environ.get("GRADLE_USER_HOME", str(Path.home() / ".gradle")))
    cache = gradle_user_home / "caches"
    cache_present = cache.exists() and any(cache.iterdir())
    result = {
        "schema": SCHEMA, "started_at": now(), "finished_at": None,
        "status": "NOT_RUN", "build_attempts": 0, "automatic_retries": 0,
        "forced_fallback": force_fallback, "required_empty_cache": require_empty_cache,
        "gradle_cache_present_at_start": cache_present,
        "source_commit": None, "expected_source_commit": os.environ.get("HEARTHBOUND_EXPECTED_COMMIT"),
        "build_input_sha256": {}, "build_exit_code": None,
        "resolved_build_environment": None, "fallback_verification": None,
        "errors": [], "evidence_errors": [],
        "limits": {"minecraft_world_started": False, "dependency_outage_established": False,
                   "immutable_build_plugin_versions_declared": False},
    }
    write_json(output / "preflight.json", result)
    exit_code = 1
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                                  capture_output=True, text=True, check=True, timeout=30)
        result["source_commit"] = revision.stdout.strip()
        if result["expected_source_commit"] and result["source_commit"] != result["expected_source_commit"]:
            raise ValueError("Checkout does not match HEARTHBOUND_EXPECTED_COMMIT.")
        result["build_input_sha256"] = {name: sha256(root / name) for name in BUILD_INPUTS}
        if require_empty_cache and cache_present:
            raise ValueError("Cold-build validation requires an initially empty Gradle cache.")
        gradle = shutil.which("gradle")
        if not gradle:
            raise FileNotFoundError("Gradle is unavailable; provision Gradle 8.8 before preflight.")
        for command, name in (([gradle, "--version"], "gradle-version.log"), (["java", "-version"], "java-version.log")):
            with (output / name).open("w") as stream:
                subprocess.run(command, cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                               check=True, timeout=60)
        command = [gradle, "--no-daemon", "--console=plain", "--stacktrace", "--info",
                   f"-PhearthboundBuildEvidenceDir={output}"]
        if force_fallback:
            command += ["--init-script", str(root / "gradle/force-forge-tool-fallback.init.gradle")]
        command += ["captureHearthboundBuildEnvironment"]
        if force_fallback:
            command += ["verifyHearthboundForgeToolFallback"]
        command += ["compileJava", "compileTestJava"]
        result.update(command=command, status="RUNNING", build_attempts=1)
        write_json(output / "preflight.json", result)
        with log_path.open("w") as stream:
            exit_code = run_build(command, root, stream, timeout_seconds)
        result["build_exit_code"] = exit_code
        result["status"] = "PASS" if exit_code == 0 else failure_status(log_path.read_text(errors="replace"), root=root)
    except subprocess.TimeoutExpired as error:
        result["status"] = "TIMED_OUT"
        result["errors"].append(f"{type(error).__name__}: {error}")
        result["evidence_errors"].append(
            "Timeout cleanup covers observed process identities; complete Gradle daemon shutdown is not independently verified.")
        result["timeout_cleanup_scope"] = "observed_descendant_process_identities"
        exit_code = 124
    except BuildCleanupError as error:
        result["status"] = "CLEANUP_FAILURE"
        result["errors"].append(str(error))
        exit_code = 1
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        result["status"] = "ENVIRONMENT_NOT_READY"
        result["errors"].append(f"{type(error).__name__}: {error}")
        exit_code = 1
    finally:
        for name, field in (("build-environment.json", "resolved_build_environment"),
                            ("fallback-verification.json", "fallback_verification")):
            path = output / name
            if path.exists():
                try:
                    result[field] = json.loads(path.read_text())
                except (OSError, ValueError) as error:
                    result["evidence_errors"].append(f"Cannot read {name}: {error}")
        result["evidence_errors"] += environment_errors(result["resolved_build_environment"])
        if force_fallback:
            result["evidence_errors"] += fallback_errors(result["fallback_verification"])
        if result["status"] == "PASS" and result["evidence_errors"]:
            result["status"] = "EVIDENCE_INCOMPLETE"
            exit_code = 2
        result["log_path"] = str(log_path)
        # Never certify a timeout log as final solely from process ancestry:
        # a daemon may have detached/reparented before the cleanup snapshot.
        result["log_finalized"] = result["status"] not in ("TIMED_OUT", "CLEANUP_FAILURE")
        result["log_sha256"] = sha256(log_path) if log_path.exists() and result["log_finalized"] else None
        result["finished_at"] = now()
        result["exit_code"] = exit_code
        write_json(output / "preflight.json", result)
        print(f"FORGE_PREFLIGHT status={result['status']} attempts={result['build_attempts']} evidence={output / 'preflight.json'}")
        if exit_code != 0 and log_path.exists():
            print("\n".join(log_path.read_text(errors="replace").splitlines()[-100:]))
    return exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path)
    parser.add_argument("--force-forge-tool-fallback", action="store_true")
    parser.add_argument("--require-empty-gradle-cache", action="store_true")
    parser.add_argument("--timeout-seconds", type=int, default=1200)
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    try:
        return run_preflight(args.output, args.log, args.force_forge_tool_fallback,
                             args.require_empty_gradle_cache, args.timeout_seconds)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    sys.exit(main())
