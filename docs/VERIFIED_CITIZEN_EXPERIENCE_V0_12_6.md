# Hearthbound v0.12.6 — Verified real citizen experience dataset

This research milestone stacks on PR #146. It exports the **actual Forge server's finalized, digest-verified attention journal** into chronological, read-only citizen experience. It does not generate synthetic observations, perform training, or infer which unselected source would have been better.

## Data provenance and replay order

`export_verified_citizen_experience.py` first verifies the saved journal against the clean-stop manifest, including full byte-level SHA-256, count and SHA-256 chain tip. It then consumes matched choice/outcome entries in source order. Every decision row contains its actual server tick, citizen UUID, dimension, registered candidates, selected source, policy, selected observed-or-unobserved sensor result, and the model-available **prior** personal source history.

The feature history for each candidate includes whether it was previously directly observed; last directly observed wheat/availability; age in ticks; direct inspection count; and the observed change rate where at least two successful inspections exist. Unknown fields remain JSON null. The chosen outcome is applied to the personal history only **after** the prior features for the decision are captured. An unsuccessful inspection does not refresh source knowledge; observations of different citizens or dimensions never share a cache.

## Training/evaluation boundaries

Every event records `unselected_outcomes=UNKNOWN`, `counterfactual_reward=null`, and `optimal_action_label=null`. These are on-policy observations of the existing scripted attention scheduler, not expert imitation labels and not a reliable off-policy return estimate. The output explicitly uses `split_unit=RUN_ID_NOT_EVENT`: all decisions from a world run must stay within the same dataset split to avoid contamination across train and test through shared time history. A single run cannot establish generalization; use independent Minecraft runs/seeds for held-out comparisons.

This version intentionally produces no gradient updates or policy deployments. The resulting JSON is suitable for causality/sensor auditing, descriptive measures of observation coverage and later safe offline model evaluation that **abstains** when an alternative outcome is unknown.

## Acceptance

- Standalone regression tests confirm no future observations enter a decision's prior features; unselected chest contents are unknown; missing/truncated manifests fail closed.
- The dedicated-server SCRIPTED and TRAINED_MLP CI arms export from actual Forge finalization files, then restart the server and export again from the saved world.
- CI compares pre-/post-restart dataset bytes and archives both exports as downloadable evidence.
- Every record has run identity, event sequence, policy and no Minecraft execution authority.

## Remaining limitations

The original opportunity set consists of registered watches, not guaranteed reachable physical choices. There are no counterfactual labels, direct collection rewards, neural exploration outcomes, policy propensities, or human-grounded societal measurements yet. This exporter provides reliable source-history chronology but does not itself prove agent learning.
