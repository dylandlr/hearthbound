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
import threading
import uuid

ROOT = Path.cwd()
CLIENT = ROOT / "client-run"
GUEST = ROOT / "guest-run"
SERVER = ROOT / "run"
OUT = ROOT / "client-evidence"
OUT.mkdir(exist_ok=True)
spec = importlib.util.spec_from_file_location("rcon", ROOT / "scripts/forge-rcon-probe.py")
rcon = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rcon)
PLAYER = "HearthboundQA"
GUEST_PLAYER = "HearthboundGuest"
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
    rcon.execute(f"execute at {WORKER} run tp {PLAYER} ~1.8 ~ ~2.2 140.71 0")


def client_check(activity, cargo, item=None, flour=None, target=None):
    follow = threading.Event()
    def track():
        while not follow.wait(.1):
            try: aim()
            except OSError: pass
    camera = threading.Thread(target=track, daemon=True)
    camera.start()
    try:
        return inspect_client(activity, cargo, item, flour, target)
    finally:
        follow.set()
        camera.join(timeout=2)


def inspect_client(activity, cargo, item=None, flour=None, target=None):
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
                  "max-players": "2", "enable-rcon": "true", "rcon.password": "hearthbound-ci-only-password",
                  "rcon.port": "25575", "view-distance": "4", "simulation-distance": "5", "allow-flight": "true"}
    (SERVER / "server.properties").write_text("\n".join(k + "=" + v for k, v in properties.items()) + "\n")
    player_id = uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + PLAYER).encode()).digest(), version=3)
    (SERVER / "ops.json").write_text(json.dumps([{"uuid": str(player_id), "name": PLAYER,
                                                "level": 4, "bypassesPlayerLimit": True}]))
    (SERVER / "user_jvm_args.txt").write_text("-Xms512M -Xmx2G\n")
    server = launch(["bash", "run.sh", "nogui"], SERVER, "server.log")
    wait_for(lambda: "Hearthbound" in rcon.execute("hearthbound status"), 150, "Forge server readiness")
    for text in ["gamerule doMobSpawning false", "gamerule doDaylightCycle false", "gamerule sendCommandFeedback false", "gamerule logAdminCommands false", "time set 6000", "weather clear"]:
        command(text)
    options = ("maxFps:30\nrenderDistance:4\nsimulationDistance:5\nguiScale:2\n"
        "fullscreen:false\npauseOnLostFocus:false\nonboardAccessibility:false\njoinedFirstServer:true\n"
        "skipMultiplayerWarning:true\ntutorialStep:none\nfov:0.0\ngamma:1.0\nsoundCategory_master:0.0\nnarrator:0\nbobView:false\n")
    (CLIENT / "options.txt").write_text(options)
    GUEST.mkdir(exist_ok=True)
    (GUEST / "options.txt").write_text(options.replace("maxFps:30", "maxFps:15").replace("renderDistance:4", "renderDistance:2"))
    (GUEST / "mods").mkdir(exist_ok=True)
    for mod in (CLIENT / "mods").glob("*.jar"):
        target = GUEST / "mods" / mod.name
        if not target.exists(): target.symlink_to(mod.resolve())
    profile = json.loads((CLIENT / "versions/1.20.1-forge-47.4.10/1.20.1-forge-47.4.10.json").read_text())
    replacements = {"library_directory": str(CLIENT / "libraries"), "classpath_separator": ":", "version_name": "1.20.1"}
    def resolve(value):
        for key, replacement in replacements.items():
            value = value.replace("${" + key + "}", replacement)
        return value
    def client_args(name, identity, game_dir, width, height, memory):
        args = ["java", "-Xms384M", "-Xmx" + memory, "-Djava.library.path=" + str(CLIENT / "natives"),
                "-Dorg.lwjgl.librarypath=" + str(CLIENT / "natives"), "-Dminecraft.launcher.brand=hearthbound-playtest",
                "-Dminecraft.launcher.version=1", "-Dhearthbound.recordWorkerViews=true",
                "-Dhearthbound.recordWorkshopControls=true"]
        args += [resolve(value) for value in profile["arguments"]["jvm"]]
        args += ["-cp", (CLIENT / "classpath.txt").read_text(), profile["mainClass"], "--username", name,
                 "--uuid", str(identity), "--accessToken", "0", "--userType", "legacy", "--version", profile["id"],
                 "--versionType", "release", "--gameDir", str(game_dir), "--assetsDir", str(CLIENT / "assets"),
                 "--assetIndex", (CLIENT / "asset-index.txt").read_text(), "--width", str(width), "--height", str(height)]
        return args + profile["arguments"]["game"] + ["--quickPlayMultiplayer", "127.0.0.1:25565"]
    game = launch(client_args(PLAYER, player_id, CLIENT, 1280, 720, "1536M"), CLIENT, "client.log")
    wait_for(lambda: PLAYER in rcon.execute("list"), 240, "graphical client joins dedicated server")
    guest_id = uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + GUEST_PLAYER).encode()).digest(), version=3)
    guest = launch(["xvfb-run", "-a", "-s", "-screen 0 640x480x24"]
                   + client_args(GUEST_PLAYER, guest_id, GUEST, 640, 480, "1024M"), GUEST, "guest-client.log")
    wait_for(lambda: PLAYER in rcon.execute("list") and GUEST_PLAYER in rcon.execute("list"),
             240, "two graphical clients join dedicated server")
    print("HB_TWO_CLIENT_JOIN_PASS owner=" + PLAYER + " guest=" + GUEST_PLAYER, flush=True)
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
                 "setblock 46 -61 3 minecraft:yellow_wool", "setblock 42 -60 0 minecraft:barrel", "setblock 49 -60 0 create:millstone",
                 "setblock 49 -61 0 create:creative_motor[facing=up]", "setblock 55 -60 0 minecraft:barrel",
                 'data merge block 42 -60 0 {Items:[{Slot:0b,id:"minecraft:wheat",Count:8b}]}',
                 'summon minecraft:villager 40.5 -60 0.5 {Tags:["hearthbound.sable"],CustomName:\'{"text":"Sable"}\',CustomNameVisible:1b,PersistenceRequired:1b}']:
        command(text)
    wait_for(lambda: "following entity data" in rcon.execute(f"data get entity {WORKER} Pos"), 10, "worker query readiness")
    aim()
    recording = launch(["ffmpeg", "-y", "-f", "x11grab", "-video_size", "1280x720", "-framerate", "20",
                        "-i", os.environ["DISPLAY"], "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "22",
                        "-pix_fmt", "yuv420p", str(OUT / "Hearthbound_Workshop_Controls.mp4")], ROOT, "capture.log")
    controls_spec = importlib.util.spec_from_file_location("controls_client", ROOT / "scripts/workshop-controls-client.py")
    controls_module = importlib.util.module_from_spec(controls_spec)
    controls_spec.loader.exec_module(controls_module)
    controls_ui = controls_module.run_setup(globals())
    deadline = time.monotonic() + 80
    saw_flour = False
    saw_mill_wait = False
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
            # Stop via the native screen while real flour is in persisted cargo.
            saved_haul = command(f'data get entity {WORKER} ForgeData.HearthboundHaul')
            controls_ui['open']()
            controls_ui['button']('stop')
            wait_for(lambda: 'HearthboundMillOrder:' not in rcon.execute(f'data get entity {WORKER} ForgeData'), 10, 'UI stops only scheduling')
            assert saved_haul == command(f'data get entity {WORKER} ForgeData.HearthboundHaul'), 'Stop changed in-flight cargo'
            screenshot("controls-stop-carrying.png")
            controls_ui['status'](['owner=You', 'access=OWNER', 'mill=SELF', 'paused=true', 'shared=0', 'manage=true', 'release=false'], 'status-paused-reservation.png')
            controls_ui['sharing'](['owner=You', 'people=1', 'manage=true', 'release=false',
                                    'selected=HearthboundGuest/false/true'], 'access-paused-reservation.png')
            controls_ui['sharing_click']('share', ['people=1', 'manage=true', 'release=false',
                                                   'selected=HearthboundGuest/true/true'])
            assert 'shared=1' in command('hearthbound workshop_status 49 -60 0')
            screenshot('access-shared-while-paused.png')
            controls_ui['sharing_back']()
            controls_ui['status_back']()
            assert saved_haul == command(f'data get entity {WORKER} ForgeData.HearthboundHaul'), 'Status page changed cargo'
            print('HB_WORKSHOP_STATUS_UI_PASS unclaimed_preview owner paused_reservation draft_preserved readonly', flush=True)
            controls_ui['button']('save')  # Disabled until this haul completes.
            assert 'HearthboundMillOrder:' not in rcon.execute(f'data get entity {WORKER} ForgeData')
            controls_ui['button']('resume')
            wait_for(lambda: 'activity=paused' not in rcon.execute('execute positioned 48 -60 0 run hearthbound worker_view'), 10, 'UI resumes retained haul')
            controls_ui['button']('close')
            wait_for(lambda: 'cargo=0' in rcon.execute('execute positioned 48 -60 0 run hearthbound worker_view'), 15, 'stopped order finishes its current haul')
            assert re.search(r'Count:\s*1b', command('data get block 55 -60 0 Items'))
            controls_ui['open']()
            controls_ui['save']()
            wait_for(lambda: 'HearthboundMillOrder:' in rcon.execute(f'data get entity {WORKER} ForgeData'), 10, 'UI restarts saved setup')
            controls_ui['button']('close')
            print('HB_WORKSHOP_STOP_RESTART_UI_PASS cargo_preserved start_disabled_during_haul UI_resume cached_setup_restarted', flush=True)
        order_state = rcon.execute(f"data get entity {WORKER} ForgeData.HearthboundMillOrder")
        if 'WaitState: "AT_WAIT"' in order_state and 'State: "MILLING"' in order_state:
            saw_mill_wait = True
        if "activity=target_reached cargo=0" in view and 'WaitState: "AT_WAIT"' in order_state:
            break
        time.sleep(.2)
    else:
        raise AssertionError("First Mill target timed out: " + view)
    assert saw_flour, "No real flour carrying phase observed"
    target = client_check("target_reached", 0, "minecraft:air", flour=2, target=2)
    time.sleep(3)
    wait_position = command(f"data get entity {WORKER} Pos")
    coords = [float(n) for n in re.findall(r"(-?\d+(?:\.\d+)?)d", wait_position)]
    assert len(coords) == 3 and 46 <= coords[0] < 47 and -60 <= coords[1] < -59 and 3 <= coords[2] < 4, wait_position
    screenshot("flour-target.png")
    controls_ui['open']()
    controls_ui['status'](['owner=You', 'access=OWNER', 'mill=FREE', 'shared=1',
                           'manage=true', 'release=true'], 'status-shared-free.png')
    controls_ui['sharing'](['owner=You', 'people=1', 'manage=true', 'release=true',
                            'selected=HearthboundGuest/true/true'], 'access-shared-free.png')
    controls_ui['sharing_click']('revoke', ['people=1', 'manage=true', 'release=true',
                                            'selected=HearthboundGuest/false/true'])
    assert 'shared=0' in command('hearthbound workshop_status 49 -60 0')
    screenshot('access-revoked.png')
    controls_ui['sharing_back']()
    controls_ui['status_back']()
    controls_ui['button']('close')
    print('HB_TWO_CLIENT_SHARING_UI_PASS online_guest grant_while_reserved persisted_until_revoke native_clicks', flush=True)
    # Keep the gameplay capture focused on the full native-control production flow.
    recording.stdin.write("q\n"); recording.stdin.flush(); recording.wait(timeout=20); recording = None
    controls_ui['open']()
    subprocess.run(['xdotool', 'windowsize', windows[-1], '640', '480'], check=True)
    wait_for(lambda: controls_ui['screen']()['width'] < 340, 10, 'small-window layout')
    small_geometry = controls_ui['screen']()
    assert small_geometry['x'] >= 0 and small_geometry['y'] >= 0 and small_geometry['height'] >= 220, small_geometry
    screenshot('controls-small-window.png')
    status_geometry = controls_ui['status'](['owner=You', 'access=OWNER', 'mill=FREE', 'shared=0', 'manage=true', 'release=true'], 'status-small-window.png')
    assert status_geometry['width'] <= 304 and status_geometry['height'] >= 220, status_geometry
    assert 183 + 9 < status_geometry['height'] - 30, status_geometry
    sharing_geometry = controls_ui['sharing'](['owner=You', 'people=1', 'manage=true', 'release=true',
                                              'selected=HearthboundGuest/false/true'], 'access-small-window.png')
    assert sharing_geometry['width'] <= 304 and sharing_geometry['height'] >= 200, sharing_geometry
    controls_ui['sharing_back']()
    controls_ui['status_back']()
    print('HB_WORKSHOP_STATUS_SMALL_WINDOW_PASS owner station_rows access_controls back_button native_640x480', flush=True)
    subprocess.run(['xdotool', 'windowsize', windows[-1], '1280', '720'], check=True)
    wait_for(lambda: controls_ui['screen']()['width'] == 340, 10, 'restored window layout')
    controls_ui['button']('close')
    print('HB_WORKSHOP_SMALL_WINDOW_PASS native_640x480_layout', flush=True)
    rendered = (OUT / "client.log").read_text()
    for witness in ["HB_CLIENT_HUD activity=picking_up", "HB_CLIENT_HUD activity=putting_down",
                    "HB_CLIENT_CARGO activity=putting_down", "HB_CLIENT_HUD activity=returning_to_workshop"]:
        assert witness in rendered, "Missing actual render witness: " + witness
    print("HB_GRAPHICAL_WORKSHOP_PASS actual_interaction_HUD cargo_reach return_to_saved_wait", flush=True)
    jar = next((SERVER / "mods").glob("hearthbound-*.jar"))
    (OUT / "provenance.json").write_text(json.dumps({"source": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "jar_sha256": hashlib.sha256(jar.read_bytes()).hexdigest(), "minecraft": "1.20.1", "forge": "47.4.10",
        "create": "6.0.8", "capture": "continuous X11 screen capture; no audio or time acceleration",
        "camera": "observer player teleported to follow worker; worker never teleported",
        "waiting_position": wait_position, "waiting_order": order_state, "observed_mill_wait": saw_mill_wait,
        "interaction_ticks": 15, "blocked_client": blocked, "delivered_client": delivered, "target_client": target, "flour_client": flour_view,
        "controls": "Actual xdotool right-click, native screen buttons, four world picks, numeric target; player de-opped before setup",
        "small_window": small_geometry, "status_small_window": status_geometry, "access_small_window": sharing_geometry,
        "status_page": "Server-authored ownership, endpoint holders and queues; unclaimed preview and paused self reservation rendered; Back preserves draft and cargo",
        "access_page": "Two actual connected clients; owner grants guest while reserved, grant persists until native revoke; release disabled while reserved and enabled once free",
        "control_stop_restart": "UI stops while flour cargo=1, haul NBT unchanged, Start disabled, UI resumes the haul, delivery finishes, UI restarts cached setup",
        "two_client_sharing": "HearthboundQA and HearthboundGuest connected concurrently; real Share/Revoke buttons confirmed by server status and server-authored render state",
        "test_pause": "first flour haul paused in persisted job for the visual/stop assertion, then resumed"}, indent=2))
    print("HB_GRAPHICAL_WORKSHOP_CONTROLS_PASS real_mouse_keyboard non_operator_setup stop_with_cargo restart_target", flush=True)
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
