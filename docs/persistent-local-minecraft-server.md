# Persistent Hearthbound Minecraft development server

Unlike the short-lived GitHub Actions GameTest server, this local server keeps its world under `run/hearthbound-dev-world` between sessions and can be joined by a matching Minecraft Forge client. It uses the project's existing `runServer` configuration (Minecraft 1.20.1 / Forge + Create), not Paper.

## Windows / PowerShell

Install Java 17 and Python 3. From a clone of this branch:

```powershell
python scripts/dev_server.py status
python scripts/dev_server.py start --accept-eula
```

**Only use `--accept-eula` if you have reviewed and accepted https://aka.ms/MinecraftEULA**. Once accepted, subsequent starts can omit it. The launcher creates an online-authenticated development world by default; edit `run/server.properties` to change port or other local settings. Do not expose the development server or Minecraft RCON to the public internet without authentication and network access controls.

## Linux / macOS

```bash
python3 scripts/dev_server.py start --accept-eula
```

Run `python3 scripts/dev_server.py status` from another terminal. Status reports recorded launcher process presence and the latest Hearthbound log markers; it does not claim real-time connection to the server or confirm a healthy tick rate. Keep the foreground launcher active while observing Minecraft; Ctrl+C stops it. A persistent **world** is not a persistent **hosting service**: it runs only while the terminal and computer stay up.

To connect visually, launch a Forge 1.20.1 client with matching Create and Hearthbound mods and connect to `localhost:25565` if client and server share a host. Use a separate client machine and its host's IP on a trusted LAN otherwise. The existing `/hearthbound status`, `/hearthbound millstone inspect <pos>` and `/hearthbound millstone trace` diagnostics are available in-game; the current mod has **no autonomous NPCs to watch yet**. Inspect `run/logs/latest.log` to see processing events and audit evidence.

For reproducible GameTests, continue running GitHub acceptance independently; `run-gametest` is intentionally separate. The new launcher has not been executed inside a Minecraft runtime in this commit.
