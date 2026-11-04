# Hearthbound v0.13.0 — Reproducible source intervention schedules on real Forge

This is stacked on PR #150. The prior world-seed metadata captured only the configured Minecraft terrain seed while each real RCON acceptance case reused the same static chest inventory fixture. This extension supplies **opt-in deterministic inventory interventions** without altering automatic pull-request acceptance.

## Workflow and evidence

Manual `workflow_dispatch` accepts `world_seed` and `resource_schedule` (default `baseline`, optional `seeded-v1`). The existing frozen smoke suite uses baseline. Both SCRIPTED and TRAINED_MLP trial arms share the selected seed and intervention schedule, preserving a matched-control comparison.

The `seeded-v1` plan is derived by SHA-256 from the configured seed and step index. Six bounded interventions alternate between chests (9,100,2) and (10,100,2), changing wheat counts among 0..4. Operators send actual `data merge block` commands to the disposable Forge server while the read-only citizen watch journal is active. Each command must be acknowledged as modified, and the harness captures actual `time query gametime` ticks before and after the intervention. The resulting `real-resource-schedule.json` and independent `verified-resource-schedule.json` bind realized RCON interventions to the precommitted plan digest. The harness restores the fixed chest fixture and directly refreshes recipient memory before the existing persistence/restart checks.

## Scientific limitations

This records **operator-executed environmental changes**, not agent-generated actions, and an executed intervention is not equivalent to a subsequent successful citizen observation. Not every resource transition is necessarily inspected. The plan does not imply truly diverse terrain or complete independence across seeds. Because the two sources remain in a controlled artificial fixture, this still cannot establish colony-level learning/generalization. Reward claims for unselected choices remain prohibited.

The manual workflow input becomes available for end-user dispatch under GitHub's branch/workflow availability rules; a draft PR alone is not evidence that the new workflow was manually dispatched.

## Acceptance

- Deterministic plan reproducibility and changed-value guarantee for each source.
- Stable SHA-256 schedule identity changes with configured world seed.
- Actual RCON mutation responses and monotonically attributed server ticks are validated.
- Baseline workflow left untouched for ordinary PR tests.
- The existing real Forge citizen NBT, social privacy, sealed decision/outcome journal, and restart integrity regressions remain required.

Next: launch independent manually seeded Forge trials and capture an actual fixture-diversity evaluation. Do not claim results from runs that have not completed.
