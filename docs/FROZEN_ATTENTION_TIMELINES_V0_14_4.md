# Hearthbound v0.14.4 — Identical latent timelines for policy comparison

## Problem

Previous synthetic comparisons generated hidden world changes inside the policy's per-step inspection routine. When policies make different inspection choices, their random-number sequences and intervening truth histories can diverge. Matching the initial random seed alone does not guarantee matched hidden trajectories. This makes direct differences less interpretable.

The real four-source Forge experiment from PR #160 remains a separate fact: a single matched configured-seed pair witnessed **8 of 16** resource changes under scripted attention and **5 of 16** under the frozen neural policy, at 10 selected-source inspections each. This does not establish a population-level causal superiority result. Nothing in the new study modifies that result or the real Forge engine.

## New simulator evaluation

`benchmark_frozen_attention_timelines.py` generates the complete sequence of four-source binary resource states **before** any attention policy acts. Source transition rates depend on the test regime and 1, 2, or 4 hidden updates between inspection opportunities. Every policy in the same evaluation episode receives the **exact same sequence of latent states at the same decision indices**.

This uses an immutable, SHA-256 signed synthetic trajectory with 32 decision steps; the shared trajectory digest is reported per training-seed/regime/rate cell. The policy cannot read trajectory states except the current chosen source value during a completed inspection. Unchosen states, future states and true source transition probabilities remain inaccessible as policy features or model-training rewards. There is one selected-source inspection per decision.

Four controls are evaluated without changing their training contracts:

- Scripted least-recently-sampled.
- Exploration-aware 16→16→4 MLP.
- History-gated exploration-aware MLP (scripted fallback).
- Observed-uncertainty-trained MLP.

Train neural candidates from scratch for each training seed (11,17,23), then evaluate four held-out regimes × three rates × 40 episodes per cell, with 32 decisions per episode. All four policies use the same frozen timeline for every episode. Report source-visit distribution, directly observed discoveries and neural-minus-scripted differences.

## What this improves

Matched simulated world histories eliminate policy-dependent *environment randomness* from the comparison. Policy choices still affect each citizen's own observation history and future decisions—this is intentional. Unlike the previous benchmark, this design supports paired comparisons against identical latent state trajectories in synthetic worlds.

**It still does not prove Minecraft generalization or statistical significance**. The transition model is synthetic, candidate hyperparameters are exploratory, world geometry is absent, and these evaluation regimes are limited. Future work should add held-out model classes, more seeds, paired confidence intervals, and controlled real Forge comparisons before any deployment decision.

## Admission and release boundaries

The existing frozen Forge model and all real Minecraft test suites remain unchanged. This is simulator-only. `minecraft_policy_deployed=false` and `model_promotion_authorized=false` are asserted by CI regardless of results. There is no RCON access, actual Minecraft outcome use, online learning, LLM, pathfinding, hauling, crafting or new task-execution authority in this change.
