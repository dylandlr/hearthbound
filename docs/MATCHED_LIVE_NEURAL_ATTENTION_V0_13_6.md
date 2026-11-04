# Hearthbound v0.13.6 — Real matched scripted versus neural attention experiment

This milestone follows PR #156, which *verified* one neural-controlled source inspection on a real Forge server. A single successful canary does not establish that neural attention improves observation coverage. Here we move neural selection into the **same six-step real Forge resource intervention schedule** already used by the scripted baseline.

## Experimental arms

The current four baseline/seeded CI arms remain intact. A **fifth disposable Forge server** is added:

- Existing scripted seeded arm: world seed `hearthbound-resource-probe-A`, fixture `chest-two-source-seeded-v1`, six seed-indexed mutations; attention remains `LEAST_RECENTLY_SAMPLED`.
- New live neural seeded arm: same configured world seed, same source coordinates, same intervention digest and six-step schedule; attention switches to `NEURAL_CAUSAL_MLP_OPT_IN` **after initial scripted acceptance and before the first scheduled mutation**, and is disabled at the recorded measurement cutoff before fixture cleanup.

The model is the simulator-trained 16→16→4 causal-history MLP whose production Java inference passed Python parity. The operator alone enables and disables the selector. The existing server gate continues to allow only one source inspection per citizen every five ticks, and source inventories are never included in pre-inspection model features. No navigation, hauling, crafting, LLMs or task-execution powers are added.

## Verification

The new real arm retains the sealed Forge attention choice/outcome journal, real RCON intervention timestamps, explicit measurement cutoff, and observation-coverage audit. A new validator requires **at least one journaled neural-policy selection inside the actual intervention interval**, all decisions inside that interval attributed to neural policy, only registered sources selected, no invented unselected outcomes or rewards, and a finalized journal. Merely loading the model or performing a post-intervention canary is insufficient.

A dedicated `compare-live-attention-arms` CI job downloads both real seed-matched arms and checks that they share the configured seed and resource schedule digest but have different experiment run IDs. It records matched direct-observation coverage, verified neural decisions and descriptive coverage difference.

## Interpretation

This is a first controlled feasibility comparison, not a randomized or multi-seed causal estimate. The arms execute separately and RCON/wall-clock scheduling can shift exact tick timing. The intervention digest ensures identical *requested resource counts*, not identical tick-aligned stimulus trajectories. Directly observed matching chest states are not guaranteed caused exclusively by the operator intervention. No reward or optimal-action label exists for unselected inspections. The trained model was developed in the simulator, not learned online in Minecraft.

**Acceptance**: full CI including original four server arms and fifth neural arm must pass before publishing any real performance numbers. Any comparison must include exact archived report provenance and distinguish objective observation coverage from claims about learning. The existing PRs remain draft; no merge is implied.
