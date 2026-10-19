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


try:
    (SERVER / "eula.txt").write_text("eula=true\n")
    flat = {"layers": [{"block": "minecraft:bedrock", "height": 1},
                        {"block": "minecraft:dirt", "height": 2},
                        {"block": "minecraft:grass_block", "height": 1}], "biome": "minecraft:plains"}
    properties = {"online-mode": "false", "enforce-secure-profile": "false", "level-name": "society-baseline",
                  "level-type": "minecraft:flat", "generator-settings": json.dumps(flat), "level-seed": "20261014",
                  "max-players": "1", "enable-rcon": "true", "rcon.password": "hearthbound-ci-only-password",
                  "rcon.port": "25575", "view-distance": "6", "simulation-distance": "5", "allow-flight": "true"}
    (SERVER / "server.properties").write_text("\n".join(k + "=" + v for k, v in properties.items()) + "\n")
    player_id = uuid.UUID(bytes=hashlib.md5(("OfflinePlayer:" + PLAYER).encode()).digest(), version=3)
    (SERVER / "ops.json").write_text(json.dumps([{"uuid": str(player_id), "name": PLAYER,
                                                "level": 4, "bypassesPlayerLimit": True}]))
    (SERVER / "user_jvm_args.txt").write_text("-Xms512M -Xmx2G\n")
    server = launch(["bash", "run.sh", "nogui"], SERVER, "server.log")
    wait_for(lambda: "bootstrap active" in rcon.execute("hearthbound status"), 150, "Forge server readiness")
    for text in ["gamerule doMobSpawning false", "gamerule doDaylightCycle false", "gamerule sendCommandFeedback false", "gamerule logAdminCommands false", "time set 6000", "weather clear"]:
        command(text)
    (CLIENT / "options.txt").write_text("maxFps:30\nrenderDistance:6\nsimulationDistance:5\nguiScale:2\n"
        "fullscreen:false\npauseOnLostFocus:false\nonboardAccessibility:false\njoinedFirstServer:true\n"
        "skipMultiplayerWarning:true\ntutorialStep:none\nfov:0.0\ngamma:1.0\nsoundCategory_master:0.0\nnarrator:0\nbobView:false\n")
    profile = json.loads((CLIENT / "versions/1.20.1-forge-47.4.10/1.20.1-forge-47.4.10.json").read_text())
    replacements = {"library_directory": str(CLIENT / "libraries"), "classpath_separator": ":", "version_name": "1.20.1"}
    def resolve(value):
        for key, replacement in replacements.items():
            value = value.replace("${" + key + "}", replacement)
        return value
    args = ["java", "-Xms512M", "-Xmx2G", "-Djava.library.path=" + str(CLIENT / "natives"),
            "-Dorg.lwjgl.librarypath=" + str(CLIENT / "natives"), "-Dminecraft.launcher.brand=hearthbound-playtest",
            "-Dminecraft.launcher.version=1", "-Dhearthbound.recordWorkerViews=true", "-Dhearthbound.recordWorkshopControls=true"]
    args += [resolve(value) for value in profile["arguments"]["jvm"]]
    args += ["-cp", (CLIENT / "classpath.txt").read_text(), profile["mainClass"], "--username", PLAYER,
             "--uuid", str(player_id), "--accessToken", "0", "--userType", "legacy", "--version", profile["id"],
             "--versionType", "release", "--gameDir", str(CLIENT), "--assetsDir", str(CLIENT / "assets"),
             "--assetIndex", (CLIENT / "asset-index.txt").read_text(), "--width", "1280", "--height", "720"]
    args += profile["arguments"]["game"] + ["--quickPlayMultiplayer", "127.0.0.1:25565"]
    game = launch(args, CLIENT, "client.log")
    def joined():
        if game.poll() is not None:
            raise AssertionError("Graphical client exited: " + (OUT / "client.log").read_text()[-6000:])
        return PLAYER in rcon.execute("list")
    wait_for(joined, 120, "graphical client joins dedicated server")
    command("gamemode creative " + PLAYER)
    time.sleep(5)
    windows = subprocess.check_output(["xdotool", "search", "--onlyvisible", "--pid", str(game.pid)], text=True).splitlines()
    if windows:
        subprocess.run(["xdotool", "windowfocus", "--sync", windows[-1]], check=True)
    command('gamemode spectator ' + PLAYER)
    for cmd in ['forceload add -16 -16 32 32',
                'fill -3 99 -3 20 99 18 minecraft:grass_block',
                'fill -3 100 -3 20 107 18 minecraft:air',
                'setblock 8 100 7 minecraft:chest replace']:
        command(cmd)
    names = ['Iris', 'Moss', 'Elara', 'Sable', 'Rowan', 'Ash', 'Fern', 'Briar']
    sources = [(2,2),(5,2),(8,2),(11,2),(14,2),(2,12),(8,12),(14,12)]
    def who(name):
        return f'execute as @e[type=minecraft:villager,name={name},limit=1] at @s run '
    for i, (name, (x,z)) in enumerate(zip(names,sources)):
        command(f'setblock {x} 100 {z} minecraft:chest{{Items:[{{Slot:0b,id:"minecraft:wheat",Count:1b}}]}} replace')
        result = command(f'execute positioned {5+i%4*2} 100 {5+i//4*4} run sable spawn-named {name}')
        assert 'citizen spawned' in result.lower(), result
        result = command(who(name)+'sable auto-work-source-discover 8 100 7')
        assert 'configured discover-source auto work' in result.lower(), result
        command(who(name)+'sable haul-priority 1')
        command(who(name)+'hearthbound library priority 0')
    command(f'tp {PLAYER} 8 116 24 180 46')
    time.sleep(3)
    subprocess.run(['xdotool','key','F1'],check=True)
    video = OUT / ('Hearthbound_Survival_Baseline.mp4' if os.environ.get('HB_CAPTURE_SURVIVAL') == '1' else 'Hearthbound_Eight_Citizens_Baseline.mp4')
    recording = subprocess.Popen(['ffmpeg','-y','-f','x11grab','-video_size','1280x720',
        '-framerate','30','-i',os.environ['DISPLAY'],'-c:v','libx264','-preset','veryfast',
        '-crf','22','-pix_fmt','yuv420p',str(video)],stdout=subprocess.DEVNULL,
        stderr=(OUT/'capture.log').open('w'),stdin=subprocess.PIPE)
    time.sleep(2)
    for name in names:
        assert 'auto work enabled' in command(who(name)+'sable auto-work-on').lower()
    # Source selection, claims, navigation and transfer are production citizen code.
    # The harness assigns only a destination and work priorities, not routes.
    wait_for(lambda: 'test passed' in rcon.execute(
        'execute if data block 8 100 7 Items[{id:"minecraft:wheat",Count:8b}]').lower(),
        180,'eight independently completed deliveries')
    for x,z in sources:
        assert 'test passed' in command(f'execute unless data block {x} 100 {z} Items[{{id:"minecraft:wheat"}}]').lower()
    evidence = {'commit': os.environ.get('GITHUB_SHA','unknown'),
        'scenario':'eight-citizen physical work baseline; no trained survival policy',
        'world_seed':20261014,'citizens':{},'inventory':{'source_before':8,'source_after':0,'destination_after':8}}
    jobs = []
    for name in names:
        status = wait_for(lambda n=name: (lambda s: s if 'haulCompleted=true' in s else None)(
            rcon.execute(who(n)+'sable auto-work-status')),30,name+' completion')
        job = re.search(r'haulJob=([0-9a-f-]{36})',status)
        assert job, status
        jobs.append(job[1])
        memory = command(who(name)+'sable social-inspect')
        assert 'source=SELF' in memory and 'WHEAT_DELIVERY' in memory, memory
        evidence['citizens'][name] = {'status':status,'memory':memory,
            'instincts':command(who(name)+'sable instinct-inspect')}
    assert len(set(jobs)) == 8, jobs
    evidence['social_web'] = command(who('Iris')+'sable social-web')
    assert 'citizens=8' in evidence['social_web'], evidence['social_web']
    screenshot('eight-citizens.png')
    if os.environ.get('HB_CAPTURE_SURVIVAL') == '1':
        command(f'tp {PLAYER} 80 120 106 180 48')
        with (OUT / 'survival-acceptance.log').open('w') as log:
            subprocess.run(['python3','-u','scripts/survival-server-test.py'],cwd=ROOT,
                           stdout=log,stderr=subprocess.STDOUT,check=True,timeout=360)
        evidence['survival_acceptance'] = 'passed; scripted-v1; one controlled citizen'
        screenshot('survival-complete.png')
    time.sleep(6)
    (OUT/'provenance.json').write_text(json.dumps(evidence,indent=2))
    print('HB_EIGHT_CITIZEN_CAPTURE_PASS: 8 distinct jobs; inventory conserved; per-citizen memories',flush=True)
except Exception:
    screenshot('failure.png')
    raise
finally:
    if recording:
        recording.communicate(b'q',timeout=20)
    for process in reversed(children):
        process.terminate()
        try: process.wait(timeout=15)
        except subprocess.TimeoutExpired: process.kill()
