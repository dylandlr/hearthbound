# Hearthbound v0.15.1 — Observed event attribution and detection latency

## Why

The new out-of-distribution stress benchmark in PR #171 passed: greedy forecast was −2.27778 direct discoveries per 64-decision episode compared to scripted rotation. The frozen age-blended predictor averaged +0.00463; the coverage guard again made zero deviations. The age-blend made around 22–24 different choices per episode but saw largely the same number of changes. This suggests that raw count alone may conceal differences in *when* a real latent event is detected.

We are **not** changing any agent policy or model weights in this milestone.

## Direct observation and hidden evaluator contract

`benchmark_attention_event_latency.py` replays the same frozen forecaster against scripted, greedy, age-blended and coverage-guard selectors. It records only the selected-source direct observation at every time step, with source ID, prior personally observed state, new state, first-visit flag and confirmed disagreement.

A separate offline evaluator then reads the pre-generated latent timeline. For a source's transition at time T, count it as witnessed only if the agent had inspected that source **before T**, reinspects it **at or after T but before its next same-source transition**, and confirms that the new directly observed value **differs from its own previous observed value**. If a transition reverses before observation, or there was no earlier baseline, do **not** invent a detection. A witnessed event's delay is the selected reinspection time minus T.

The evaluator additionally reports: all latent transitions, baseline-eligible transitions, events witnessed before their next same-source transition, events not witnessed, total/average detection delay for witnessed events, total direct reinspection disagreements, nonproductive reinspections and first inspections. Strict regression fixtures cover immediate detection, unseen reversal and missing pre-transition baselines. The metric is a synthetic world-observer audit, *not* a reward or observation provided to an agent.

## Experimental design

Reuse exactly the three previously precommitted novel stress schedules from PR #171: permanent depletion, unannounced bursts and long gaps, each 64 decisions. Freeze the existing GRU forecaster once per seed (11,17,23), with 180 original training episodes; compare all four unchanged policies on 24 independently generated timelines per seed/schedule. Report signed latent timeline manifests, frozen model parameter hashes and per-episode paired event-detection differences relative to scripted selection. No parameters are tuned on outcomes.

This evaluation avoids conflating first-time resource discovery (which may reward any source on its first visit) with actual detection of **changes since a known observation**. However, detection latency is conditional on detected events: it must be reported alongside missed-event counts, not alone, because a policy could obtain a small average delay by missing slower events.

## Boundaries

All data are simulated. The real Forge four-source attention challenge remains a separate experiment in which scripted attention witnessed 8/16 operator mutations and the deployed frozen MLP 5/16. None of those results train this forecaster or adjust decision thresholds. No Minecraft weights, mods, live tasks, LLMs, or RCON authority are modified or deployed. The project still requires independently held-out real Forge evaluations before claiming runtime generalization.
