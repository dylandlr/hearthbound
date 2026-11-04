# Hearthbound v0.12.8 — Run-level real attention shadow analysis

This research-only milestone follows PR #148 and aggregates **completed Minecraft experiment runs**, never individual within-run decisions as independent replicates. It preserves policy agreement and uncertainty about unselected resources; it does not infer rewards or train/deploy a model.

## Input and integrity

`scripts/aggregate_real_attention_runs.py` consumes one or more independently exported `real-attention-shadow-after-restart.json` reports from the validated Forge evidence chain. Each source must carry the expected versioned schema, the original source journal file SHA, finalized run ID, `REAL_FORGE_OFFLINE_SHADOW` origin, simulated-only neural training origin, explicit non-execution / no-counterfactual flags and a correct self-hash. It also checks policy agreement counts, unknown alternative counts and the actual recommendation list for consistency. Duplicate run IDs are rejected, even if submitted under separate paths.

This source self-hash is an integrity check, **not** a trusted signature or independent evidence of Minecraft-world authenticity; provenance still depends on retaining and validating the original sealed server journal.

## Analysis

The three registered policies are:
- Simulator-trained causal-history MLP
- Unknown-first-then-oldest observation heuristic
- First-registered baseline

For each policy, report per-run agreement count, disagreement count, selected-outcome coverage and the number of unknown unselected alternatives, plus an **unweighted mean** of *per-run agreement rates*. Per-decision total agreements are descriptive only. No reward advantage, optimal action, neural improvement claim, off-policy return estimate or statistical significance is calculated.

The output explicitly sets:
- `unit_of_analysis=RUN`
- `independence_verified=false`
- `world_seed_provenance_available=false`
- `generalization_claim_allowed=false`
- `statistical_significance_claimed=false`
- `reward_comparison_performed=false`
- `minecraft_actions_authorized=false`

## Dedicated Minecraft acceptance

The CI compare-policy-arms job downloads the SCRIPTED and TRAINED_MLP trial artifacts from two real dedicated Forge runs, each of which has been reconstructed from a manifest-sealed journal and validated across restart. The new job runs synthetic regression fixtures for aggregator integrity and then produces `real-attention-run-level-analysis.json` as a comparison artifact.

**Important confound**: both existing dedicated-server arms use the same configured Minecraft world seed and scripted resource fixtures. Their run IDs are separate, but they are **not independent world-seed samples** and cannot establish generalization. The summary is explicitly descriptive, rather than a held-out experiment.

## Required next experiment

Collect multiple genuinely distinct Minecraft world seeds and resource-change schedules, record a machine-readable seed/fixture identifier in trusted run metadata, and ensure complete-run train/validation/test separation. Make source candidates and recording policy explicit and monitor recording effects on Minecraft TPS. Only after independent-run evidence is available should confidence intervals and experimental model comparisons be attempted. An agreement measure alone still cannot identify counterfactual rewards.
