# Hearthbound — Dedicated-server startup gate

The existing [Forge Create integration checks](../.github/workflows/forge-create-checks.yml) successfully compile and package a Forge 1.20.1 mod JAR. This is **not** evidence that the mod has loaded in Minecraft.

A second manually dispatched workflow, `Hearthbound dedicated server smoke test`, attempts to launch ForgeGradle's `runServer` dev runtime with the mod on its classpath. Its EULA-acceptance input must be explicitly selected by the triggering user before it runs. EULA: https://www.minecraft.net/en-us/eula.

## Run instructions

1. In GitHub → Actions → Hearthbound dedicated server smoke test → Run workflow, choose branch `feat/create-forge-dependency-v1-2`.
2. Read and accept the Minecraft EULA using the workflow input if you agree to it.
3. Run the workflow; review the `Boot Forge development server` output and uploaded logs.
4. Confirm the log shows a Minecraft server-ready message and no mod-loading crash.

This smoke test launches the **development** server, not a production deployment, and no remote players are expected to connect. `online-mode=false` is used only for the isolated ephemeral CI instance. Do not reuse the generated server.properties in public multiplayer deployments.

## Passing is insufficient for gameplay readiness

- Verify Create is actually loaded in logs and its required runtime dependencies are present.
- Verify `/hearthbound status` and `/hearthbound millstone inspect <x> <y> <z>` in a controlled in-game session.
- Verify machine inputs and outputs via mutation-time server evidence, not inventory snapshots.
- Verify the persistent journal and reward deduplication after a server restart.
- Replace the current single-machine diagnostic with an actual Create operation event integration.

This workflow is staged, **not run yet**. No live Minecraft startup or working in-game command is claimed.
