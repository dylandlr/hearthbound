#!/usr/bin/env python3
"""Prepare official 1.20.1 client assets/libraries for the disposable graphical CI check.
Forge's normal installer has already installed the production client profile.
Audio objects are unnecessary for this intentionally silent screen capture.
"""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path.cwd()
CLIENT = ROOT / "client-run"
LIBRARIES = CLIENT / "libraries"
ASSETS = CLIENT / "assets"


def fetch(url, path, expected=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and (expected is None or hashlib.sha1(path.read_bytes()).hexdigest() == expected):
        return
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=90) as response:
                data = response.read()
            if expected and hashlib.sha1(data).hexdigest() != expected:
                raise ValueError("SHA-1 mismatch for " + path.name)
            temporary = path.with_suffix(path.suffix + ".download")
            temporary.write_bytes(data)
            temporary.replace(path)
            return
        except Exception:
            if attempt == 2:
                raise


def allowed(library):
    rules = library.get("rules", [])
    result = not rules
    for rule in rules:
        platform = rule.get("os", {})
        if platform.get("name", "linux") == "linux" and not rule.get("features"):
            result = rule["action"] == "allow"
    return result


manifest = json.load(urllib.request.urlopen("https://piston-meta.mojang.com/mc/game/version_manifest_v2.json", timeout=45))
version = next(v for v in manifest["versions"] if v["id"] == "1.20.1")
version_path = CLIENT / "versions/1.20.1/1.20.1.json"
fetch(version["url"], version_path, version["sha1"])
vanilla = json.loads(version_path.read_text())
client_jar = version_path.with_suffix(".jar")
fetch(vanilla["downloads"]["client"]["url"], client_jar, vanilla["downloads"]["client"]["sha1"])
profile = json.loads((CLIENT / "versions/1.20.1-forge-47.4.10/1.20.1-forge-47.4.10.json").read_text())
jobs = {}
for library in vanilla["libraries"]:
    if not allowed(library):
        continue
    downloads = library["downloads"]
    artifacts = [downloads["artifact"]] if "artifact" in downloads else []
    native = library.get("natives", {}).get("linux")
    if native:
        artifacts.append(downloads["classifiers"][native])
    for artifact in artifacts:
        jobs[artifact["path"]] = (artifact["url"], LIBRARIES / artifact["path"], artifact["sha1"])
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    list(pool.map(lambda args: fetch(*args), jobs.values()))
index = vanilla["assetIndex"]
index_path = ASSETS / "indexes" / (index["id"] + ".json")
fetch(index["url"], index_path, index["sha1"])
objects = json.loads(index_path.read_text())["objects"]
jobs = {}
for name, entry in objects.items():
    if name.endswith(".ogg") or "/sounds/" in name:
        continue
    digest = entry["hash"]
    jobs[digest] = ("https://resources.download.minecraft.net/" + digest[:2] + "/" + digest,
                    ASSETS / "objects" / digest[:2] / digest, digest)
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
    list(pool.map(lambda args: fetch(*args), jobs.values()))
natives = CLIENT / "natives"
natives.mkdir(exist_ok=True)
for jar in LIBRARIES.rglob("*natives-linux*.jar"):
    with zipfile.ZipFile(jar) as archive:
        for name in archive.namelist():
            if name.endswith(".so"):
                (natives / Path(name).name).write_bytes(archive.read(name))
classpath = []
for library in profile["libraries"] + vanilla["libraries"]:
    if not allowed(library):
        continue
    artifact = library.get("downloads", {}).get("artifact")
    if artifact:
        path = LIBRARIES / artifact["path"]
    else:
        group, name, version, *classifier = library["name"].split(":")
        filename = name + "-" + version + ("-" + classifier[0] if classifier else "") + ".jar"
        path = LIBRARIES / group.replace(".", "/") / name / version / filename
    if not path.exists():
        raise FileNotFoundError(path)
    if path not in classpath:
        classpath.append(path)
classpath.append(client_jar)
(CLIENT / "classpath.txt").write_text(os.pathsep.join(map(str, classpath)))
(CLIENT / "asset-index.txt").write_text(index["id"])
print("HB_CLIENT_PREPARED official libraries, non-audio assets, natives and Forge profile", flush=True)
