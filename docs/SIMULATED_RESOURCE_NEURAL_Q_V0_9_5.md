# Hearthbound v0.9.5 — First reward-trained v2 neural benchmark (SIMULATED)

## Context / verified predecessor

PR #114's v0.9.4 Forge/Create CI and both dedicated-server trials passed, including live ten-feature tensor observations and restart-aware reward contracts. That verified neural **input acquisition**, not learning. The previous 5→12→4 mill MLP and source-aware scripted planner remain frozen as controls.

## New learner

A small neural Q-value approximator (10 inputs, 20 ReLU hidden units, three output Q-values) is trained with temporal-difference targets, replay and a lagged target network. **This is real weight optimization driven by rewards**, rather than imitation labels. It uses only Python's standard library; no LLM or pretrained game knowledge.

Its three high-level simulated actions:

- \`INSPECT_SOURCE\`: reveal the simulated wheat-source state locally, with no resource creation
- \`WAIT_FOR_SUPPLY\`: wait while an exogenous source has a chance to restock
- \`REQUEST_WHEAT_HAUL\`: request hauling only after confirming available wheat; a premature request is rejected and penalized

The state is the ordered 10-feature \`hearthbound.mill-observation.v2\` tensor from PR #114. The abstract world fixes mill power and excludes real Create processing, pathfinding and combat. Its simulated resource dynamics are **not** Minecraft dynamics.

Reward bookkeeping is split into colony (production reward and time/invalid-request costs) and personal (verified simulated task success); Q learning optimizes their sum in this first benchmark. This is a **new simulator reward contract**, not the audited real Minecraft mill-reward.v1 or an update to Sable's production experience.

## Scientific comparison

Training and held-out evaluation seeds are disjoint. Every held-out world is evaluated using an independently initialized environment with the **same seed and initial supply conditions** across (a) trained neural Q, (b) source-aware scripted reference and (c) untrained neural network. Metrics include task success, mean steps, invalid requests, personal and colony rewards.

The CLI explicitly emits:

- \`training_data_origin=SIMULATED_ONLY\`
- \`minecraft_execution_claimed=false\`
- \`minecraft_learning_claimed=false\`
- \`environment=abstract fast simulated wheat availability\`

CI runs deterministic safety and reproducibility tests, trains a bounded short benchmark, and uploads \`simulated-mill-neural-q-results.json\`. It must not be mixed into the audited \`minecraft-experience-dataset.json\`.

## Frozen experimental checkpoint

The simulation training workflow also saves `simulated-mill-neural-q-checkpoint.json` as a versioned 10→20→3 neural weight artifact. A deterministic SHA-256 covers the canonical payload, including feature order, action labels, architecture, weights and training provenance. Loading it requires matching the complete contract and finite weights. Unit tests verify exact round-trip Q-value parity and reject tampered checksums and wrong-sized matrices.

The checkpoint explicitly sets `minecraft_deployment_authorized=false` and `training_data_origin=SIMULATED_ONLY`. No checksum alone makes a simulator-trained model safe to run in Minecraft.

## Interpretation / next integration

Even if neural Q achieves high success in its toy environment, **that is not evidence of improved Minecraft intelligence**. The input sensor has been grounded in Minecraft; the simplified transition/reward process has not. Before any world-changing neural control:

1. Expand the real Minecraft observation ledger to include action/observation **sequences**, masks and world outcomes, not just successful terminal task receipts.
2. Replace toy transition assumptions with measured mechanisms or use domain randomization and explicit simulator-to-Minecraft validation.
3. Export a checksum-verified new model with separate model ID; demonstrate Java/Python numeric parity and correct action masks.
4. Run a fixed, read-only neural shadow evaluation in real Minecraft across held-out sources before authorizing a restricted one-shot policy request.
5. Compare against scripted and frozen v1 policies using matched worlds and multiple episodes, separating the safety gate from learned decisions.

This milestone is a **trainable DL baseline**, not autonomous agent behavior or deployment.
