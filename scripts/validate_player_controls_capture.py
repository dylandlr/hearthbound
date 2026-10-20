#!/usr/bin/env python3
"""Validate that an actual Minecraft player-controls recording was produced."""
import json
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "gameplay-capture")
video = root / "minecraft-player-controls.mp4"
log = root / "player-control-inputs.log"
required = (
    "player-default-perspective.png", "player-cutaway-on.png",
    "player-cutaway-off.png", "player-first-person.png",
    "player-return-tactical.png", "player-after-click.png",
)
if not video.is_file() or video.stat().st_size < 10000:
    raise SystemExit("Missing or empty actual player-controls MP4")
for name in required:
    file = root / name
    if not file.is_file() or file.stat().st_size < 1000:
        raise SystemExit("Missing screenshot evidence: " + name)
if not log.is_file():
    raise SystemExit("Missing input transcript")
transcript = log.read_text()
for action in ("pan arrows", "switch to first person V",
               "return tactical V", "click citizen selection"):
    if action not in transcript:
        raise SystemExit("Missing recorded input: " + action)
probe = subprocess.run(
    ["ffprobe", "-v", "error", "-show_entries",
     "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
    capture_output=True, text=True, check=True)
duration = float(probe.stdout.strip())
if duration < 20:
    raise SystemExit(f"Player-controls recording too short: {duration:.1f}s")
subprocess.run(["ffmpeg", "-hide_banner", "-v", "error", "-xerror",
                "-i", str(video), "-f", "null", "-"],
               check=True, capture_output=True)
print(json.dumps({"recording": str(video), "duration_seconds": duration,
                  "screenshots": len(required), "input_transcript": str(log),
                  "result": "evidence files valid; visual behavior requires review"}))
