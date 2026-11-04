# Hearthbound v0.13.1 — Auditing which real resource interventions citizens witnessed

This milestone stacks on PR #151. The prior seeded-resource experiment records the exact **operator-executed** RCON mutations of two Forge chest inventories, while the existing sealed attention journal records which sources citizens **directly inspected**. Those two facts must not be conflated. The new audit joins them conservatively.

## Evidence inputs

- `real-resource-schedule.json`: six verified RCON mutations, their actual Minecraft tick boundaries, the configured seed, and the precommitted schedule SHA-256.
- `attention-<run-id>.jsonl`: real citizen pre-inspection decision and selected-source outcome records, verified with its finalized manifest and complete file digest.
- `real-world-provenance.json`: optional configuration evidence tying the schedule to the configured world seed and the `chest-two-source-seeded-v1` fixture.

## Conservative observation windows

For each intervention, consider only direct `OBSERVED` outcomes on the **same selected source**, strictly after the recorded `tick_after`, strictly before the next operator mutation of that same source, and no later than the final scheduled intervention. Observations in the mutation tick are not credited because exact ordering within the tick is not proven. A matching wheat quantity establishes a directly witnessed state **consistent with** that intervention in the allowed interval; it does not prove exclusive causation or that no other actor modified the chest.

The output contains per-intervention counts of observations that match or disagree with the intervention's recorded post-mutation wheat quantity, the first matching observation tick, an explicit `witnessed_expected_state` boolean, and a cohort coverage rate. Interventions lacking an eligible matching direct observation remain **unwitnessed**, not failures of the neural policy.

## Integrity and limitations

Both real RCON provenance and the clean-stop manifest must validate before the auditor emits results. The output marks all unselected alternatives as unknown, authorizes no Minecraft actions, and claims no learning superiority. The direct source candidates still originate from operator registrations, not autonomous discovery.

The baseline pull-request smoke suite runs deterministic audit regression fixtures but does **not** execute the opt-in seeded intervention schedule. When manual `workflow_dispatch.resource_schedule=seeded-v1` is executed, the dedicated-server run will also generate `verified-intervention-observation-coverage.json` from actual Minecraft evidence and archive it with the underlying schedule and sealed journal.

Next: run multiple configured world seeds with held-out resource schedules and measure how often the scripted citizen actually witnesses changes, before attempting a live learned attention policy. Do not infer counterfactual rewards for choices never executed.
