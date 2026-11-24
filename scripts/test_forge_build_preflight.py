#!/usr/bin/env python3
"""Failure-preserving build evidence tests; these do not simulate a Forge pass."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from run_forge_build_preflight import BUILD_INPUTS, failure_status, run_build, run_preflight, signal_build

COMMIT = "a" * 40
HASH = "b" * 64


def repository_policy():
    return {
        "policy": "exclude-mapped-versions-once-v1", "version_pattern": ".*_mapped_.*",
        "upstream_repeated_filter_enabled": False, "generated_repositories_exempt": True,
        "external_repositories": [{"name": "HearthboundForgeInstallerToolsFallback", "applications": 1}],
    }


def environment():
    return {
        "schema": "hearthbound-forge-build-environment-v1",
        "gradle_version": "8.8", "java_runtime_version": "17.0.21+9",
        "java_vendor": "test fixture", "configured_java_toolchain_language_version": 17,
        "mapped_repository_filter": repository_policy(),
        "resolved_build_plugins": [
            {"group": "net.minecraftforge.gradle", "name": "ForgeGradle",
             "resolved_version": "fixture-version", "artifact_sha256": HASH},
            {"group": "org.spongepowered", "name": "mixingradle",
             "resolved_version": "fixture-version", "artifact_sha256": HASH},
        ],
    }


def fallback():
    exclusions = [{"name": "HearthboundForgeInstallerToolsFallback",
                   "mapped_installer_excluded": True, "unmapped_installer_excluded": False}]
    return {
        "schema": "hearthbound-forge-tool-fallback-v1", "status": "PASS",
        "forced_maven_exclusions": ["MavenRepo"], "repositories_restored": True,
        "resolution_path": "forgegradle_non_maven_gradle_fallback", "artifact_sha256": HASH,
        "mapped_repository_filter": repository_policy(), "mapped_exclusions_before": exclusions,
        "mapped_exclusions_after": exclusions, "mapped_version_exclusions_verified": True,
    }


class BuildPreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in BUILD_INPUTS:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("fixture input " + name)
        self.output = self.root / "evidence"
        self.calls = []
        self.build_returncode = 0
        self.build_log = "BUILD SUCCESSFUL (unit-test subprocess fixture only)\n"
        self.emit_environment = True
        self.emit_fallback = False
        self.fallback_override = None
        self.environment_override = None
        self.timeout = False
        self.env_patch = patch.dict("os.environ", {
            "GRADLE_USER_HOME": str(self.root / "gradle-user"),
            "HEARTHBOUND_EXPECTED_COMMIT": COMMIT,
        })
        self.env_patch.start()
        self.addCleanup(self.env_patch.stop)

    def fake_run(self, command, **kwargs):
        self.calls.append(command)
        if command[:2] == ["git", "rev-parse"]:
            return subprocess.CompletedProcess(command, 0, COMMIT + "\n", "")
        kwargs["stdout"].write("fixture launcher version\n")
        return subprocess.CompletedProcess(command, 0)

    def fake_build(self, command, root, stream, timeout_seconds):
        self.calls.append(command)
        stream.write(self.build_log)
        if self.emit_environment:
            (self.output / "build-environment.json").write_text(json.dumps(
                self.environment_override if self.environment_override is not None else environment()))
        if self.emit_fallback:
            (self.output / "fallback-verification.json").write_text(json.dumps(
                self.fallback_override if self.fallback_override is not None else fallback()))
        if self.timeout:
            raise subprocess.TimeoutExpired(command, timeout_seconds)
        return self.build_returncode

    def execute(self, **kwargs):
        with patch("run_forge_build_preflight.shutil.which", return_value="/fixture/gradle"), \
                patch("run_forge_build_preflight.subprocess.run", side_effect=self.fake_run), \
                patch("run_forge_build_preflight.run_build", side_effect=self.fake_build), \
                contextlib.redirect_stdout(io.StringIO()):
            code = run_preflight(self.output, root=self.root, **kwargs)
        return code, json.loads((self.output / "preflight.json").read_text())

    def test_one_attempt_keeps_resolved_artifacts_and_build_inputs(self):
        code, result = self.execute(require_empty_cache=True)
        self.assertEqual((code, result["status"], result["build_attempts"]), (0, "PASS", 1))
        self.assertEqual(result["resolved_build_environment"], environment())
        self.assertEqual(set(result["build_input_sha256"]), set(BUILD_INPUTS))
        self.assertEqual(len(result["log_sha256"]), 64)
        self.assertFalse(result["limits"]["minecraft_world_started"])
        commands = [command for command in self.calls if "compileJava" in command]
        self.assertEqual(len(commands), 1)
        self.assertNotIn("--init-script", commands[0])
        self.assertNotIn("verifyHearthboundForgeToolFallback", commands[0])

    def test_dependency_failure_retains_first_log_and_provenance_without_retry(self):
        self.build_returncode = 1
        self.build_log = ("Could not resolve all files for configuration ':mavenDownloader_1'.\n"
                          "Cannot resolve external dependency net.minecraftforge:installertools:1.4.4 "
                          "because no repositories are defined.\n")
        code, result = self.execute()
        self.assertEqual((code, result["status"]), (1, "DEPENDENCY_RESOLUTION_FAILURE"))
        self.assertEqual(result["resolved_build_environment"], environment())
        self.assertEqual((self.output / "gradle.log").read_text(), self.build_log)
        self.assertEqual(sum("compileJava" in command for command in self.calls), 1)
        self.assertFalse(result["limits"]["dependency_outage_established"])

    def test_source_error_is_not_promoted_to_dependency_failure(self):
        log = "Could not resolve noise\nsrc/Thing.java:41: error: cannot find symbol\n"
        self.assertEqual(failure_status(log), "SOURCE_COMPILATION_FAILURE")

    def test_success_without_resolved_artifact_evidence_fails_gate(self):
        self.emit_environment = False
        code, result = self.execute()
        self.assertEqual((code, result["status"]), (2, "EVIDENCE_INCOMPLETE"))
        self.assertEqual(result["build_exit_code"], 0)
        self.assertTrue(result["evidence_errors"])

    def test_forced_path_requires_actual_fallback_evidence(self):
        code, result = self.execute(force_fallback=True)
        self.assertEqual((code, result["status"]), (2, "EVIDENCE_INCOMPLETE"))
        command = next(command for command in self.calls if "compileJava" in command)
        self.assertIn("--init-script", command)
        self.assertLess(command.index("verifyHearthboundForgeToolFallback"), command.index("compileJava"))

    def test_forced_path_with_complete_evidence_retains_the_verification(self):
        self.emit_fallback = True
        code, result = self.execute(force_fallback=True)
        self.assertEqual((code, result["status"]), (0, "PASS"))
        self.assertEqual(result["fallback_verification"], fallback())

    def test_restored_repository_names_without_preserved_filters_cannot_pass(self):
        self.emit_fallback = True
        self.fallback_override = fallback()
        self.fallback_override["mapped_exclusions_after"] = [
            {"name": "HearthboundForgeInstallerToolsFallback",
             "mapped_installer_excluded": False, "unmapped_installer_excluded": False}]
        code, result = self.execute(force_fallback=True)
        self.assertEqual((code, result["status"]), (2, "EVIDENCE_INCOMPLETE"))
        self.assertTrue(any("before and after" in error for error in result["evidence_errors"]))

    def test_success_with_upstream_repeated_callback_enabled_cannot_pass(self):
        self.environment_override = environment()
        self.environment_override["mapped_repository_filter"]["upstream_repeated_filter_enabled"] = True
        code, result = self.execute()
        self.assertEqual((code, result["status"]), (2, "EVIDENCE_INCOMPLETE"))
        self.assertTrue(any("repeated callback disabled" in error for error in result["evidence_errors"]))

    def test_timeout_is_not_retried_or_recorded_as_a_world_outcome(self):
        self.timeout = True
        code, result = self.execute()
        self.assertEqual((code, result["status"]), (124, "TIMED_OUT"))
        self.assertEqual(result["build_attempts"], 1)
        self.assertIsNone(result["build_exit_code"])
        self.assertFalse(result["limits"]["minecraft_world_started"])
        self.assertFalse(result["log_finalized"])
        self.assertIsNone(result["log_sha256"])
        self.assertTrue(result["evidence_errors"])

    def test_cold_gate_rejects_existing_cache_before_build(self):
        cache = self.root / "gradle-user/caches"
        cache.mkdir(parents=True)
        (cache / "existing-artifact").write_text("fixture cache")
        code, result = self.execute(require_empty_cache=True)
        self.assertEqual((code, result["status"], result["build_attempts"]), (1, "ENVIRONMENT_NOT_READY", 0))
        self.assertTrue(result["gradle_cache_present_at_start"])
        self.assertFalse(any("compileJava" in command for command in self.calls))

    def test_checkout_mismatch_is_preserved_before_gradle_starts(self):
        with patch.dict("os.environ", {"HEARTHBOUND_EXPECTED_COMMIT": "c" * 40}):
            code, result = self.execute()
        self.assertEqual((code, result["build_attempts"]), (1, 0))
        self.assertIn("Checkout does not match", result["errors"][0])

    def test_reusing_evidence_path_cannot_erase_an_earlier_failure(self):
        self.build_returncode = 1
        _, result = self.execute()
        original = (self.output / "preflight.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "evidence already exists"):
            run_preflight(self.output, root=self.root)
        self.assertEqual((self.output / "preflight.json").read_bytes(), original)
        self.assertEqual(result["status"], "BUILD_FAILURE")

    def test_cleanup_never_signals_a_reused_launcher_or_child_pid(self):
        with patch("run_forge_build_preflight.process_identity", return_value={"started": "new"}), \
                patch("run_forge_build_preflight.os.kill") as kill, \
                patch("run_forge_build_preflight.os.killpg") as killpg:
            signal_build(42, {42: {"started": "old"}, 43: {"started": "old"}}, 15)
        kill.assert_not_called()
        killpg.assert_not_called()

    @unittest.skipUnless(sys.platform == "linux", "CI uses Linux process identities")
    def test_timeout_stops_a_child_that_outlives_the_launcher_before_log_hashing(self):
        child = self.root / "writer.py"
        child.write_text(
            "import os, signal, time\n"
            "from pathlib import Path\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "Path('child.pid').write_text(str(os.getpid()))\n"
            "while True:\n"
            "    print('still-writing', flush=True)\n"
            "    time.sleep(0.02)\n"
        )
        launcher = self.root / "launcher.py"
        launcher.write_text(
            "import subprocess, sys, time\n"
            "subprocess.Popen([sys.executable, 'writer.py'], start_new_session=True)\n"
            "time.sleep(60)\n"
        )
        log = self.root / "timeout.log"
        with log.open("w") as stream:
            with self.assertRaises(subprocess.TimeoutExpired):
                run_build([sys.executable, str(launcher)], self.root, stream, 1,
                          termination_grace_seconds=1)
        self.assertTrue((self.root / "child.pid").exists(), "Child must start for this cleanup check")
        frozen = log.read_bytes()
        self.assertIn(b"still-writing", frozen)
        time.sleep(0.1)
        self.assertEqual(log.read_bytes(), frozen, "Timed-out descendants must not change retained evidence")


if __name__ == "__main__":
    unittest.main()
