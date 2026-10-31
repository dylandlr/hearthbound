#!/usr/bin/env python3
"""Local persistent Forge/Create dev-server launcher and read-only inspection."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
WORLD = ROOT / "run"
LOG = WORLD / "logs" / "latest.log"
STATE = WORLD / "hearthbound-dev-server.json"

def status():
    if not STATE.exists():
        print("No locally recorded Hearthbound dev-server session.")
    else:
        info = json.loads(STATE.read_text(encoding="utf-8"))
        pid = int(info["pid"])
        alive = False
        try:
            os.kill(pid, 0)
            alive = True
        except (OSError, ValueError):
            pass
        print(f"Session pid={pid} process_present={alive} started={info['started']}")
        print("Process presence does not prove Minecraft readiness; inspect latest.log.")
    print(f"World directory: {WORLD}")
    if LOG.exists():
        lines = LOG.read_text(encoding="utf-8", errors="replace").splitlines()
        matching = [line for line in lines if
                    any(key in line for key in ("HEARTHBOUND_", "Done (", "Exception in server tick loop"))]
        print("\n".join(matching[-25:]) if matching else "No Hearthbound diagnostics found.")
    else:
        print("No server log found.")

def launch(accept_eula):
    WORLD.mkdir(parents=True, exist_ok=True)
    eula = WORLD / "eula.txt"
    if not eula.exists() or "eula=true" not in eula.read_text(encoding="utf-8"):
        if not accept_eula:
            raise SystemExit("Minecraft EULA not accepted locally. Review https://aka.ms/MinecraftEULA and rerun start --accept-eula only if you agree.")
        eula.write_text("eula=true\n", encoding="utf-8")
    props = WORLD / "server.properties"
    if not props.exists():
        props.write_text(
            "level-name=hearthbound-dev-world\n"
            "online-mode=true\n"
            "enable-command-block=false\n"
            "spawn-protection=0\n"
            "motd=Hearthbound Persistent Development\n",
            encoding="utf-8")
    gradle = ROOT / ("gradlew.bat" if os.name == "nt" else "gradlew")
    command = [str(gradle), "--no-daemon", "runServer"]
    print("Starting Forge + Create in foreground. Keep this terminal running to retain the server.")
    print("Stop cleanly with Ctrl+C; back up run/hearthbound-dev-world between experiments.")
    STATE.write_text(json.dumps({"pid": os.getpid(), "started": datetime.now(timezone.utc).isoformat(),
                                  "command": command}, indent=2), encoding="utf-8")
    try:
        return subprocess.call(command, cwd=ROOT)
    finally:
        STATE.unlink(missing_ok=True)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    start = sub.add_parser("start", help="Launch persistent local server in foreground")
    start.add_argument("--accept-eula", action="store_true", help="Explicitly acknowledge reviewed Minecraft EULA")
    sub.add_parser("status", help="Inspect local process record and Hearthbound logs")
    args = parser.parse_args()
    if args.cmd == "status":
        status()
        return 0
    return launch(args.accept_eula)

if __name__ == "__main__":
    sys.exit(main())
