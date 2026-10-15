#!/usr/bin/env python3
"""Actual Forge/Create two-worker contention and graceful save/restart acceptance."""
import importlib.util
import pathlib
import sys
import time

spec = importlib.util.spec_from_file_location("shared_rcon", pathlib.Path(__file__).with_name("forge-rcon-probe.py"))
rcon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcon)

def command(text, expected):
    result = rcon.execute(text)
    print(result, flush=True)
    if expected not in result:
        raise AssertionError(text + ": " + result)
    return result

def await_marker(text, marker, seconds):
    for attempt in range(seconds * 2):
        result = rcon.execute(text)
        if "HB_SHARED_WORKSHOP_FAIL" in result:
            raise AssertionError(result)
        if marker in result:
            print(result, flush=True)
            return result
        if attempt % 10 == 0:
            print(result, flush=True)
        time.sleep(.5)
    raise AssertionError("Shared workshop timed out: " + result)

if sys.argv[1] == "stage":
    rcon.execute("forceload add 128 128 159 143")
    command("hearthbound ci_workshop_shared_start", "HB_SHARED_WORKSHOP_STARTED")
    await_marker("hearthbound ci_workshop_shared_check", "HB_SHARED_WORKSHOP_STAGED", 40)
    # Let the other scheduler retry against a stopped, paused worker's held lease.
    time.sleep(3)
    command("hearthbound ci_workshop_shared_check", "HB_SHARED_WORKSHOP_STAGED")
    command("save-all flush", "Saved")
    rcon.execute("stop")
elif sys.argv[1] == "after-restart":
    # The Java witness requires a lease read from disk, not merely recreated on tick.
    command("hearthbound ci_workshop_shared_restart", "HB_SHARED_WORKSHOP_RESTART_PASS")
    time.sleep(3)
    command("hearthbound ci_workshop_shared_restart", "HB_SHARED_WORKSHOP_RESTART_PASS")
    command("hearthbound ci_workshop_shared_resume", "HB_SHARED_WORKSHOP_RESUMED")
    await_marker("hearthbound ci_workshop_shared_done", "HB_SHARED_WORKSHOP_PASS", 90)
    time.sleep(3)
    command("hearthbound ci_workshop_shared_done", "HB_SHARED_WORKSHOP_PASS")
    print("HB_SHARED_WORKSHOP_NO_REPLAY_PASS", flush=True)
    rcon.execute("stop")
else:
    raise ValueError("Use stage or after-restart")
