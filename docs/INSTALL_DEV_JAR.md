# Install the Hearthbound development JAR

## Build provenance
GitHub Actions workflow: **Minecraft playtest JAR** (`.github/workflows/playtest-jar.yml`).
The artifact is produced by `gradle --no-daemon clean build` with Temurin Java 17 and Gradle 8.8. Its success is not evidence that the client starts or gameplay works.

## Download
1. Open the GitHub Actions tab for this repository.
2. Select **Minecraft playtest JAR** and a successful run for the exact candidate commit. Record the commit and JAR SHA-256; do not substitute an artifact from another branch.
3. Download the artifact called `hearthbound-minecraft-1.20.1-dev-jar`.
4. Extract the ZIP. Use the compiled JAR within, not the ZIP.

## Install and test
- Use Minecraft **1.20.1** with **Forge 47.4.10**.
- Use a 64-bit **Java 17** runtime for this pinned candidate.
- Install the **Minecraft 1.20.1 Forge release of Create 6.0.8**, which is now a mandatory dependency. Verify the release JAR's required/bundled dependencies; developer `slim` artifacts are not a ready-to-use modpack. Do not install duplicate nested libraries.
- Put the built mod JAR into your test installation's `mods/` directory.
- Launch a disposable test world, confirm `/hearthbound status`, then `/sable spawn`.
- Follow `docs/PLAYABLE_MILESTONE.md` to test navigation, wheat hauling, source claims and recovery.
- Use the same approved mod versions and configuration on both clients and the dedicated server. The compiled development JAR is not yet a validated multiplayer pack.
- Follow [the staged multiplayer readiness plan](SOCIETY_AND_MULTIPLAYER_ROADMAP.md) before opening access or inviting players. CI's offline-mode/RCON settings are not deployment defaults.

## Troubleshooting
- Save `logs/latest.log` and any crash reports, plus commit SHA and Forge version.
- If the JAR fails to load, treat this as a failed game smoke test despite successful compilation.
- Avoid real player inventories and valuable cargo. Transfers are not crash-atomic.
