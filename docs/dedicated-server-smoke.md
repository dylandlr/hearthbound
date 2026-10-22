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

## GitHub Actions dispatch availability

GitHub normally requires a `workflow_dispatch` workflow file to exist on the repository default branch before the manual **Run workflow** control is exposed. This smoke-test workflow is currently only on the draft feature branch; its dispatch UI may therefore not be available yet. Do not merge PR #76 merely to work around that. A maintainer can choose to land the reviewed, standalone workflow on the default branch before launching it, while keeping Create integration code in draft.

The smoke test additionally requires the literal Hearthbound bootstrap log marker, rather than accepting generic Minecraft server readiness as proof of Hearthbound loading. A successful run still does not demonstrate millstone processing or the research journal.

## Feature-branch push dispatch (v3.2)

To permit testing without merging the unverified integration into main, the smoke workflow also listens for pushes to the feature branch. The job is **skipped** unless the repository owner has explicitly set repository Actions variable `MINECRAFT_EULA_ACCEPTED` to the exact string `true` after reviewing and agreeing to the Minecraft EULA. This is a consent gate, not an automatic assertion of acceptance.

From GitHub: Settings → Secrets and variables → Actions → Variables → New repository variable. Name: `MINECRAFT_EULA_ACCEPTED`, Value: `true` (only if accepted). A future push touching the workflow, source, or build files can then trigger the smoke job on this branch. Set it back to `false` to stop automatic test server launches.

The earlier workflow_dispatch path remains; GitHub may not surface Run workflow until the file exists on the default branch. No user acceptance has been inferred or applied. Do not reuse the isolated CI server's `online-mode=false` setting on public deployments.
