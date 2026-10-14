#!/usr/bin/env python3
"""Fetch a pinned Create release and mandatory Modrinth dependencies into CI mods/.
CI-only: downloads public released mod jars, never commits them to git.
"""
import json
import pathlib
import urllib.parse
import urllib.request

BASE = "https://api.modrinth.com/v2"
OUT = pathlib.Path("run/mods")
OUT.mkdir(parents=True, exist_ok=True)
seen = set()

def api(path):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "hearthbound-ci/0.1 (mod compatibility test)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return json.load(r)

def install(project, pinned=None):
    if project in seen:
        return
    seen.add(project)
    query = urllib.parse.urlencode({"game_versions": '["1.20.1"]', "loaders": '["forge"]'})
    versions = api("/project/" + urllib.parse.quote(project, safe="") + "/version?" + query)
    if pinned is not None:
        versions = [v for v in versions if v["version_number"].startswith(pinned)]
    versions = [v for v in versions if v.get("version_type") == "release"]
    if not versions:
        raise RuntimeError("No compatible Forge release for " + project)
    version = versions[0]
    jars = [f for f in version["files"] if f["filename"].endswith(".jar")]
    jar = next((f for f in jars if f.get("primary")), jars[0] if jars else None)
    if jar is None:
        raise RuntimeError("No release jar for " + project)
    path = OUT / pathlib.Path(jar["filename"]).name
    print("Installing", version["name"], "->", path, flush=True)
    req = urllib.request.Request(jar["url"], headers={"User-Agent": "hearthbound-ci/0.1"})
    with urllib.request.urlopen(req, timeout=120) as src, path.open("wb") as dst:
        while data := src.read(262144):
            dst.write(data)
    for dep in version.get("dependencies", []):
        if dep.get("dependency_type") == "required":
            if dep.get("project_id"):
                install(dep["project_id"])
            elif dep.get("version_id"):
                item = api("/version/" + dep["version_id"])
                install(item["project_id"])

install("create", "6.0.8")
