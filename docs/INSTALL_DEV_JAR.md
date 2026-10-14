# Install the Hearthbound development JAR

## Build provenance
GitHub Actions workflow: **Minecraft playtest JAR** (`.github/workflows/playtest-jar.yml`).
The artifact is produced by `gradle --no-daemon clean build` with Temurin Java 17 and Gradle 8.8. Its success is not evidence that the client starts or gameplay works.

## Download
1. Open the GitHub Actions tab for this repository.
2. Select **Minecraft playtest JAR** and a successful run on the playtest artifact branch.
3. Download the artifact called `hearthbound-minecraft-1.20.1-dev-jar`.
4. Extract the ZIP. Use the compiled JAR within, not the ZIP.

## Install and test
- Use Minecraft **1.20.1** with **Forge 47.4.10**.
- Put the built mod JAR into your test installation's `mods/` directory.
- Launch a disposable test world, confirm `/hearthbound status`, then `/sable spawn`.
- Follow `docs/PLAYABLE_MILESTONE.md` to test navigation, wheat hauling, source claims and recovery.
- Do not install Create yet for this milestone: real Create integration is unimplemented and unverified.

## Troubleshooting
- Save `logs/latest.log` and any crash reports, plus commit SHA and Forge version.
- If the JAR fails to load, treat this as a failed game smoke test despite successful compilation.
- Avoid real player inventories and valuable cargo. Transfers are not crash-atomic.
