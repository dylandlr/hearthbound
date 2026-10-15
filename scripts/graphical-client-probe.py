#!/usr/bin/env python3
"""Actual Forge client/server cargo and HUD check with an uncut, silent X11 recording.
Only the observer camera is teleported. Workers move through the production controllers.
Run under xvfb-run after prepare-minecraft-client.py and the normal Forge installers.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import time
import uuid

ROOT = Path.cwd()
CLIENT = ROOT / "client-run"
SERVER = ROOT / "run"
OUT = ROOT / "client-evidence"
OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("rcon", ROOT / "scripts/forge-rcon-probe.py")
rcon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcon)
PLAYER = "HearthboundQA"
WORKER = "@e[type=minecraft:villager,tag=hearthbound.sable,limit=1]"
children = []
recording = None


def launch(args, cwd, log):
    stream = (OUT / log).open("w")
    process = subprocess.Popen(args, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                               stdin=subprocess.PIPE, text=True)
    children.append(process)
    return process


def command(text):
    response = rcon.execute(text)
    print(text, "=>", response[:1200], flush=True)
    return response


def wait_for(test, seconds, label):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = test()
            if result:
                return result
        except (OSError, TimeoutError):
            pass
        time.sleep(.25)
    raise AssertionError("Timed out: " + label)


def screenshot(name):
    subprocess.run(["ffmpeg", "-y", "-f", "x11grab", "-video_size", "1280x720", "-i",
                    os.environ["DISPLAY"], "-frames:v", "1", str(OUT / name)],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


def aim():
    # Camera only, outside the worker's route, close enough for the normal entity picker.
    rcon.execute(f"execute at {WORKER} run tp {PLAYER} ~1.8 ~ ~2.2 facing entity {WORKER} eyes")


def client_check(activity, cargo, item=None, flour=None, target=None):
    aim()
    time.sleep(1.5)
    log = OUT / "client.log"
    offset = log.stat().st_size
    subprocess.run(["xdotool", "key", "t"], check=True)
    time.sleep(.25)
    subprocess.run(["xdotool", "type", "--clearmodifiers", "--delay", "15", "/hearthbound_client_view"], check=True)
    subprocess.run(["xdotool", "key", "Return"], check=True)
    def new_line():
        with log.open() as stream:
            stream.seek(offset)
            lines = stream.read().splitlines()
        return next((line for line in lines if "HB_CLIENT_VIEW activity=" in line), None)
    line = wait_for(new_line, 15, "client presentation diagnostic")
    print(line, flush=True)
    for token in ["activity=" + activity, "cargo=" + str(cargo)]:
        assert token in line, line
    if item is not None:
        assert "item=" + item in line, line
    if flour is not None:
        assert "flour=" + str(flour) in line, line
    if target is not None:
        assert "target=" + str(target) in line, line
    assert int(re.search(r"hudFrames=(\d+)", line)[1]) > 0, line
    frames = int(re.search(r"cargoFrames=(\d+)", line)[1])
    assert (frames > 0) if cargo else (frames == 0), line
    return line


try:
    (SERVER / "eula.txt").write_text("eula=true\n")
    flat = {"layers": [{"block": "minecraft:bedrock", "height": 1},
                        {"block": "minecraft:dirt", "height": 2},
                        {"block": "minecraft:grass_block", "height": 1}], "biome": "minecraft:plains"}
    properties = {"online-mode": "false", "enforce-secure-profile": "false", "level-name": "visual-ci",
                  "level-type": "minecraft:flat", "generator-settings": json.dumps(flat), "level-seed": "20261014",
                  "max-players": "1", "enable-rcon": "true", "rcon.password": "hearthbound-ci-only-password",
                  "rcon.port": "25575", "view-distance": "4", "simulation-distance": "5", "allow-flight": "true"}
    (SERVER / "server.properties").write_text("\n".join(k + "=" + v for k, v in properties.items()) + "\n")
    player_id = uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + PLAYER).encode()).digest(), version=3)
    (SERVER / "ops.json").write_text(json.dumps([{"uuid": str(player_id), "name": PLAYER,
                                                "level": 4, "bypassesPlayerLimit": True}]))
    (SERVER / "user_jvm_args.txt").write_text("-Xms512M -Xmx2G\n")
    server = launch(["bash", "run.sh", "nogui"], SERVER, "server.log")
    wait_for(lambda: "Hearthbound" in rcon.execute("hearthbound status"), 150, "Forge server readiness")
    for text in ["gamerule doMobSpawning false", "gamerule doDaylightCycle false", "time set 6000", "weather clear"]:
        command(text)
    (CLIENT / "options.txt").write_text("maxFps:30\nrenderDistance:4\nsimulationDistance:5\nguiScale:2\n"
        "fullscreen:false\npauseOnLostFocus:false\nonboardAccessibility:false\njoinedFirstServer:true\n"
        "skipMultiplayerWarning:true\nfov:0.0\ngamma:1.0\nsoundCategory_master:0.0\nnarrator:0\nbobView:false\n")
    profile = json.loads((CLIENT / "versions/1.20.1-forge-47.4.10/1.20.1-forge-47.4.10.json").read_text())
    replacements = {"library_directory": str(CLIENT / "libraries"), "classpath_separator": ":", "version_name": "1.20.1"}
    def resolve(value):
        for key, replacement in replacements.items():
            value = value.replace("${" + key + "}", replacement)
        return value
    args = ["java", "-Xms512M", "-Xmx2G", "-Djava.library.path=" + str(CLIENT / "natives"),
            "-Dorg.lwjgl.librarypath=" + str(CLIENT / "natives"), "-Dminecraft.launcher.brand=hearthbound-playtest",
            "-Dminecraft.launcher.version=1"]
    args += [resolve(value) for value in profile["arguments"]["jvm"]]
    args += ["-cp", (CLIENT / "classpath.txt").read_text(), profile["mainClass"], "--username", PLAYER,
             "--uuid", str(player_id), "--accessToken", "0", "--userType", "legacy", "--version", profile["id"],
             "--versionType", "release", "--gameDir", str(CLIENT), "--assetsDir", str(CLIENT / "assets"),
             "--assetIndex", (CLIENT / "asset-index.txt").read_text(), "--width", "1280", "--height", "720"]
    args += profile["arguments"]["game"] + ["--quickPlayMultiplayer", "127.0.0.1:25565"]
    game = launch(args, CLIENT, "client.log")
    wait_for(lambda: PLAYER in rcon.execute("list"), 200, "graphical client joins dedicated server")
    command("gamemode creative " + PLAYER)
    time.sleep(5)
    windows = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--pid", str(game.pid)], text=True).splitlines()
    if windows:
        subprocess.run(["xdotool", "windowfocus", "--sync", windows[-1]], check=True)
    assert "HB_HAUL_E2E_STARTED" in command("hearthbound ci_haul_block_after_pickup")
    wait_for(lambda: "HB_HAUL_CARGO_BLOCKED_PASS" in rcon.execute("hearthbound ci_haul_check"), 50, "blocked cargo")
    blocked = client_check("output_full", 4, "minecraft:wheat")
    time.sleep(2)
    screenshot("cargo-blocked.png")
    recording = launch(["ffmpeg", "-y", "-f", "x11grab", "-video_size", "1280x720", "-framerate", "20",
                        "-i", os.environ["DISPLAY"], "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                        "-pix_fmt", "yuv420p", str(OUT / "Hearthbound_Cargo_Progress.mp4")], ROOT, "capture.log")
    time.sleep(5)
    packed = int(re.search(r":\s*(-?\d+)L?\s*$", command(f"data get entity {WORKER} ForgeData.HearthboundHaul.To"))[1])
    x, y, z = packed >> 38, packed & 4095, (packed >> 12) & ((1 << 26) - 1)
    if y >= 2048: y -= 4096
    if z >= 1 << 25: z -= 1 << 26
    command(f"data merge block {x} {y} {z} {{Items:[]}}")
    wait_for(lambda: "cargo=0 item=minecraft:air" in rcon.execute("hearthbound worker_view"), 15, "delivered cargo clears")
    delivered = client_check("idle", 0, "minecraft:air")
    assert re.search(r"Count:\s*4b", command(f"data get block {x} {y} {z} Items"))
    assert re.search(r"Count:\s*4b", command(f"data get block {x - 7} {y} {z} Items"))
    screenshot("cargo-delivered.png")
    command(f"kill {WORKER}")  # Completed disposable fixture only; no in-flight cargo.
    time.sleep(1.5)
    for text in ["forceload add 32 0 63 15", "fill 37 -61 -3 58 -61 5 minecraft:oak_planks",
                 "setblock 42 -60 0 minecraft:barrel", "setblock 49 -60 0 create:millstone",
                 "setblock 49 -61 0 create:creative_motor[facing=up]", "setblock 55 -60 0 minecraft:barrel",
                 'data merge block 42 -60 0 {Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]}',
                 'summon minecraft:villager 40.5 -60 0.5 {Tags:["hearthbound.sable"],CustomName:\'{"text":"Sable"}\',CustomNameVisible:1b,PersistenceRequired:1b}']:
        command(text)
    wait_for(lambda: "following entity data" in rcon.execute(f"data get entity {WORKER} Pos"), 10, "worker query readiness")
    assert "enabled" in command("execute positioned 40 -60 0 run hearthbound mill_order 42 -60 0 49 -60 0 55 -60 0")
    command("execute positioned 40 -60 0 run hearthbound mill_order_target 2")
    deadline = time.monotonic() + 80
    saw_flour = False
    while time.monotonic() < deadline:
        aim()
        view = rcon.execute("execute positioned 48 -60 0 run hearthbound worker_view")
        if "cargo=1 item=create:wheat_flour" in view and not saw_flour:
            saw_flour = True
            # Hold the persisted job at its normal destination for an exact
            # client-side flour check, then resume the same cargo and order.
            command(f'data merge entity {WORKER} {{ForgeData:{{HearthboundHaul:{{Paused:1b}}}}}}')
            time.sleep(3)
            flour_view = client_check("paused", 1, "create:wheat_flour")
            screenshot("flour-carrying.png")
            command(f'data merge entity {WORKER} {{ForgeData:{{HearthboundHaul:{{Paused:0b}}}}}}')
        if "activity=target_reached cargo=0" in view:
            break
        time.sleep(.2)
    else:
        raise AssertionError("First Mill target timed out: " + view)
    assert saw_flour, "No real flour carrying phase observed"
    target = client_check("target_reached", 0, "minecraft:air", flour=2, target=2)
    time.sleep(3)
    screenshot("flour-target.png")
    jar = next((SERVER / "mods").glob("hearthbound-*.jar"))
    (OUT / "provenance.json").write_text(json.dumps({"source": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "jar_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(), "minecraft": "1.20.1", "forge": "47.4.10",
        "create": "6.0.8", "capture": "continuous X11 screen capture; no audio or time acceleration",
        "camera": "observer player teleported to follow worker; worker never teleported",
        "blocked_client": blocked, "delivered_client": delivered, "target_client": target, "flour_client": flour_view,
        "test_pause": "first flour haul paused in persisted job for the visual assertion, then resumed"}, indent=2))
    print("HB_GRAPHICAL_CARGO_PROGRESS_PASS real packets, cargo rendering, HUD rendering, delivery clear and flour target", flush=True)
except Exception:
    try: screenshot("failure.png")
    except Exception: pass
    raise
finally:
    if recording is not None and recording.poll() is None:
        recording.stdin.write("q\n")
        recording.stdin.flush()
        recording.wait(timeout=20)
    try:
        rcon.execute("save-all flush")
        rcon.execute("stop")
        server.wait(timeout=35)
    except Exception:
        pass
    for child in reversed(children):
        if child.poll() is None:
            child.terminate()
