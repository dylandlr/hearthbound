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

## First verified CI experiment — run 41747455123

The simulator-only job completed successfully, including reproducibility/hidden-state contracts and the paired bootstrap evaluation. Report digest: `6efc1194e3f9082787125a679878e7e64f8870ffe85db2f76b4d5650ab4d64dc`.

Paired **mean change in discoveries per 32-inspection episode (trained MLP minus scripted)**:

| Training seed | Normal | High volatility | Low volatility | Unequal volatility |
|---|---:|---:|---:|---:|
| 11 | -0.15 | +1.83 | -0.19 | +4.27 |
| 17 | +0.26 | +2.14 | -0.37 | +5.01 |
| 23 | -0.55 | +1.94 | -0.61 | +2.03 |

Per-training-seed bootstrap intervals are retained in the generated CI JSON and stdout log; they are not pooled across training seeds. For the high-volatility scenario, all three seed-specific episode-bootstrap 95% intervals excluded zero on the positive side. For the normal scenario, all three intervals included zero. Low-volatility performance was negative for all seeds (two intervals entirely negative).

**Interpretation**: the trained model adapts favorably in the simulated rapidly changing and heterogeneous regimes but does not reliably dominate least-recently-inspected rotation. The hypothetical volatility input directly informs its decision and could be a substantial source of advantage; it is NOT yet a learned real-world estimate. Follow-up must ablate this privileged input, replace it with causal observation-history estimates, and compare performance on independent test seeds before any stronger generalization claims.
