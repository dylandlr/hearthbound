#!/usr/bin/env python3
"""Package replayable metadata about a Forge smoke run. Never claim game success from CI alone."""
import argparse
import hashlib
import json
import os
from pathlib import Path

MARKERS = (
    "HEARTHBOUND_GAMETEST_PASS inventory_identity",
    "HEARTHBOUND_GAMETEST_PASS unpowered_millstone",
    "HEARTHBOUND_GAMETEST_PASS milling_motor_connection",
    "HEARTHBOUND_MILLSTONE_MUTATION ",
    "HEARTHBOUND_RESTART_PASS observation=",
    "HEARTHBOUND_MACHINE_CHECKPOINT_PASS operation=",
    "HEARTHBOUND_DISCOVERY_RESTART_PASS operation=",
    "HEARTHBOUND_CITIZEN_CREDIT_FIXTURE_PASS ",
    "HEARTHBOUND_CITIZEN_CREDIT_RESTART_PASS operation=",
    "HEARTHBOUND_SERVER_READY createLoaded=true",
    "HEARTHBOUND_MACHINE_HANDOFF_RESTART_PASS previousCitizen=",
    "HEARTHBOUND_TWO_REAL_MILLINGS_PASS ",
)
LOGS = ("gametest.log", "server-smoke.log")

def make_manifest(root):
    files = {}
    for name in LOGS:
        path = root / name
        if not path.is_file():
            files[name] = {"present": False}
            continue
        data = path.read_bytes()
        text = data.decode("utf-8", errors="replace")
        files[name] = {
            "present": True,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "marker_counts": {m: text.count(m) for m in MARKERS},
            "errors": [s for s in text.splitlines()
                       if any(k in s for k in ("Exception in server tick loop", "Mod loading has failed",
                                               "Failed to start the minecraft server"))][:20],
        }
    # Outcomes are claims only if the required run logs exist and markers are present.
    game = files["gametest.log"]
    server = files["server-smoke.log"]
    game_markers = MARKERS[:4] + (MARKERS[7], MARKERS[11])
    server_markers = MARKERS[4:7] + (MARKERS[8], MARKERS[9], MARKERS[10])
    game_evidence = bool(game.get("present")) and all(game["marker_counts"][m] == 1 for m in game_markers)
    server_evidence = bool(server.get("present")) and all(server["marker_counts"][m] >= 1 for m in server_markers)
    return {
        "schema": "hearthbound.experiment.evidence.v1",
        "repository": os.getenv("HB_REPOSITORY", "unknown"),
        "run_id": os.getenv("HB_RUN_ID", "unknown"),
        "run_attempt": os.getenv("HB_RUN_ATTEMPT", "unknown"),
        "commit_sha": os.getenv("HB_COMMIT", "unknown"),
        "git_ref": os.getenv("HB_REF", "unknown"),
        "job_status": os.getenv("HB_JOB_STATUS", "unknown"),
        "gameplay_markers_observed": game_evidence,
        "restart_markers_observed": server_evidence,
        "verified_runtime": bool(game_evidence and server_evidence and os.getenv("HB_JOB_STATUS") == "success"),
        "files": files,
        "notes": "Marker presence is not video capture; runtime verdict also requires a successful CI job.",
    }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evidence")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    manifest = make_manifest(Path(args.root))
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("HEARTHBOUND_EVIDENCE_MANIFEST", out / "manifest.json")
    print("runtime_verified=", manifest["verified_runtime"])

if __name__ == "__main__":
    main()
