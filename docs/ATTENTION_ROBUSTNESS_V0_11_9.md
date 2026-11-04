# Hearthbound v0.11.9 — Multi-seed attention robustness (simulator only)

This is a **research evaluation harness**, stacked on PR #139. The previous single-seed experiment (500 train episodes, 120 held-out episodes) yielded 15.81667 discoveries/episode for scripted rotation versus 15.64167 for trained MLP. This next test is deliberately not tuned on those held-out observations.

## Frozen comparison
- Independent training seeds: 11, 17, 23; 500 training episodes each.
- Four evaluation regimes: original synthetic distribution, increased volatility, reduced volatility, and intentionally heterogeneous source volatility.
- 100 held-out episodes per model and regime; exactly 32 inspection decisions in each episode.
- Scripted least-recently-inspected baseline unchanged.
- Compare using paired **episode-level** differences between policies operating on the same seeded simulated world trajectories.
- 500 deterministic bootstrap replicates per model/regime, resampling paired episodes to estimate a descriptive 95% interval. These intervals **do not** include variability between training seeds.
- Record both discovery counts and proxy reward. Do not aggregate confidence intervals as though individual episodes from differently trained models were independent samples from one model.
- Preserve all per-(training seed, evaluation regime) results and metadata as a JSON CI artifact with a SHA-256 integrity hash.

## What the model may observe
Each source retains the synthetic observation tuple (unknown bit, previously observed availability bit, capped observation age, exogenous volatility). The volatile source parameter remains a simulator-known feature. Hidden current availability is excluded and tested by flipping it without changing the input. This must not be mistaken for real citizen access to true volatility in Minecraft.

## Acceptance
The standalone Python test enforces determinism, disjoint training/evaluation seeds, one inspection per decision, bounded per-episode discovery counts, hidden-state exclusion, no Minecraft deployment, and failure on duplicate training seeds or invalid experiment budgets.

## Interpretation guardrails
- A positive paired mean difference is not by itself evidence of improved Minecraft performance.
- Bootstrap intervals are exploratory and based on a finite seeded synthetic benchmark; broad claims require more independent training runs and held-out world distributions.
- Use real Forge receipts only for chronological **offline shadow replay** after v0.11.7 passes full dedicated-server acceptance; never use a future observation to choose a past action.
- No neural control over resource movement, source watch registration, or Create machinery.
