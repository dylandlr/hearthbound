# Hearthbound v0.10.1 — Resource Seeking and Occupation Switching (SIMULATED)

## Motivating question

The frozen v0.10.0 neural Q models matched scripted controls across most five resource regimes. They performed poorly when there was no available wheat because the three-action task space allowed only inspection, waiting and requesting the same haul. This milestone introduces an additional **abstract option to seek an alternate wheat source and complete another colony job**.

No Minecraft action is enabled; the development environment remains the authoritative place to test actual Create tasks.

## Versioned experimental observation/action contracts

`hearthbound.resource-task-observation.v1` is a **new 15-feature simulator-only schema**. It consists of mill power, input/output/blocked, experience, primary-source UNKNOWN/EMPTY/AVAILABLE, task-active and stale flags, alternate-source UNKNOWN/EMPTY/AVAILABLE, and observed alternate-job availability/completion. It is **not** the verified Minecraft ten-feature v2 tensor and cannot silently substitute for it.

Six high-level simulated actions: `INSPECT_PRIMARY`, `INSPECT_ALTERNATE`, `HAUL_PRIMARY`, `HAUL_ALTERNATE`, `DO_OTHER_JOB`, and `WAIT`. Neither source's inventory is revealed without inspection. Requests from unknown/empty/stale sources are masked, with server-style invalid-request checks still applied inside the simulator. Other-job completion is separately reported, not equated with producing flour.

A fresh reward-trained 15→24→6 neural Q network learns with temporal-difference targets, replay and a lagged target network. The training dataset has synthetic resource dynamics and no expert action labels.

## Evaluation

Three training seeds 11/13/17; 350 episodes per model in CI. Each frozen model is evaluated against the scripted reference and an untrained network on **six** scenarios: standard, primary empty, both empty, alternate empty, no secondary job, and a supply shift. Forty held-out episode seeds per scenario and model, matched across all three policy families, produce a transparent **3 × 6 × 40** comparison.

Metrics separately track flour success, alternate hauling, other occupation jobs, denied requests, steps, timeouts, colony reward and personal reward. Checkpoint SHA-256 values are verified unchanged after evaluation. CI includes deterministic environment/reward/masking tests, a real alternate-source workflow in the simulated colony, and explicit no-Minecraft-provenance assertions.

## Research limits

- Inventory restocking, alternative occupations, source counts and rewards are assumptions of the fast simulator, not measured Minecraft dynamics.
- A scripted policy is still a high bar. Similar neural/scripted scores do not establish neural superiority.
- Real Minecraft task switching needs actual pathfinding, source/destination claim arbitration, worker allocation, interruptions, job scheduling and persisted citizen memory.
- These tasks should be introduced as **hierarchical policy intents**, preserving existing Forge task-authority gates and the v2 Minecraft observation contract until separately expanded and verified.
- No LLMs, no live neural control, no model promotion, and no Minecraft-reward learning are claimed.

Next, assess errors in the held-out results and design a multi-citizen job board with observations based on bounded local knowledge, plus actual operational resource seeking in a fresh verified server once the upstream Maven TLS chain is healthy.
