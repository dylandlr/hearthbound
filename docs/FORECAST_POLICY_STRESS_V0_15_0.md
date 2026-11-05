# Hearthbound v0.15.0 — Out-of-distribution attention-policy stress test

## Motivation

In the prior frozen-forecaster benchmark (#170), the age-blended policy averaged +0.314 directly observed synthetic source changes over scripted across 36 evaluation groups, but it lost in ordinary and low-volatility environments, with 15 negative groups. The coverage guard never made a different choice from scripted rotation, so its zero difference is not evidence of a useful neural hybrid.

We will **not tune** the policy's 0.35 age blend using the previous held-out scores. Instead, preserve the trained forecaster, its original simulated training distribution, and the scripted/greedy/age-blend/coverage-guard decision rules, and test on precommitted novel latent dynamics.

## New resource schedules

- `permanent_depletion`: four resources begin available and each independently becomes permanently unavailable at an unobserved time between decisions 8 and horizon−8.
- `bursty_mutations`: each source undergoes a separate short ten-step burst of frequent state changes, with rare changes outside the burst; bursts are not announced to agents.
- `long_observation_gaps`: four independent sources remain unchanged through long intervals and undergo a single unannounced change each during a 64-decision episode.

These are **synthetic stress tests**, not real Minecraft inventories, and do not assert physically realistic inventory depletion or production. The distinction is whether directly witnessed source disagreement and decision coverage generalize to unexpected dynamics.

## Experimental contracts

Each trained GRU uses the same previously defined selected-source-only Bernoulli forecasting objective and 180 training episodes per seed. None of these three schedules appears in the training corpus. Freeze the GRU parameters once for each seed (11,17,23), record their SHA-256 digest, and evaluate all four previously committed attention rules against the same 64-step latent timeline. Each policy receives only its chosen source's current state during a direct inspection; no hidden or future states are exposed.

The held-out benchmark has three seeds × three new schedules × 24 independent synthetic timelines = **216 paired replay episodes**. Report direct discoveries, source visit diversity, deviations from scripted, and per-episode paired differences for later statistical evaluation. All new schedules and observation contracts have deterministic/tamper-rejection tests. Results cannot be used to change candidate parameters and then be called untouched held-out data.

## Release and attribution boundary

A gain on a synthetic stress test does not establish real Forge success. No model weights or agents are deployed in Minecraft; no LLMs, online learning, pathfinding, hauling, crafting, or task authority. Scripted and original frozen Forge MLP controls remain untouched. A viable candidate would need additional independent training seeds, confidence intervals, better normal/low-volatility behavior, and a new controlled real Forge run with matched server-observed interventions.
