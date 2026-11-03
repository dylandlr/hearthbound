# Hearthbound v0.9.8 — Pinned real Minecraft observation replay

The current Forge and playtest-JAR workflows encountered external Create/Flywheel Maven SSL certificate-chain failures, which prevent a fresh end-to-end comparison even though our standalone neural parity suite passes.

This independent workflow reuses **genuine, previously recorded** Forge/Create observations, not fabricated Minecraft logs. The source is successful GitHub Actions run [41588317216](https://github.com/dylandlr/hearthbound/actions/runs/41588317216) with pinned head commit `c1bad2309172ea8ce3196a9cccee67a743d3e058` and artifacts from the SCRIPTED and TRAINED_MLP server arms.

The replay checks the source run was successful and matches its expected commit before downloading any artifacts. Both retrieved RCON logs are independently re-parsed for valid v2 ten-feature Minecraft states, source-aware scripted plans and observed gameplay trial outcomes. We regenerate the known simulator-only neural checkpoint (seed=11, 300 simulated episodes), verify all 48 Java/Python score/action parity fixtures, then run the standalone Java neural shadow against the original RCON logs.

The output `replay-real-minecraft-shadow.json` includes source-run identity, all Q scores, action agreements and `evaluation_mode=OFFLINE_REPLAY_OF_PREVIOUS_REAL_MINECRAFT_OBSERVATIONS`. It explicitly sets `game_actions_authorized=false` and `minecraft_learning_demonstrated=false`.

**Scope:** This is an offline **counterfactual policy-decision evaluation** using real recorded observations, not a new Minecraft session, not live inference attached to Sable, not observed consequences of the model's proposed actions, and not a demonstration that simulator-trained Q values are calibrated to Minecraft rewards. Two arms record the same three controlled resource states, so they must not be counted as six statistically independent worlds.

Replay is a diagnostic workaround for the transient/untrusted Maven availability problem. We must still restore a dependable fresh Forge CI build and evaluate broader, held-out worlds before any deployment.
