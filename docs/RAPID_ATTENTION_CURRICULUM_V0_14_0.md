# Hearthbound v0.14.0 — Rapid-attention learning curriculum (simulator only)

## Motivation

The original causal-history attention MLP was pretrained on four independent synthetic sources that changed on relatively simple observation intervals. The real Forge v0.13.7 seeded two-source runs verified 41 neural inspections across three seeds and both scripted/neural arms witnessed all 18 interventions, but descriptive first-witness latency favored the scripted selector. The higher-contention **rapid four-source** real-server experiment in PR #160 is a separate, still-to-be-verified benchmark.

Before modifying any live model weights, assess whether training on *intermittently observed, rapidly changing, unequal resource sources* changes held-out synthetic discovery performance.

## Implemented research design

`scripts/benchmark_rapid_attention_curriculum.py` trains two 16→16→4 MLPs from scratch using only **the selected source's observed state** for learning. Source truth and per-source true volatility never enter model features; the only policy features are unknown/known status, last observed availability, age since last direct inspection, and the empirical observed-change rate from previous inspected states.

The two training conditions are:

- **Legacy-style:** standard in-distribution dynamics, one latent resource update per inspection.
- **Mixed rapid curriculum:** pretraining episodes rotate through in-distribution, unequal-volatility and high-volatility dynamics, with 1, 2 or 4 hidden world updates between inspections.

Both policies have one selected-source observation per decision, the same architecture and number of train episodes, identical evaluation seeds, and no train/evaluation episode overlaps. The synthetic environment advances the hidden states of all resources after each inspected-source reward, but never supplies uninspected resource truth to the MLP.

Held-out evaluation covers 4 regimes × 3 dynamics rates, including low volatility not included in mixed training. Compare each MLP to scripted least-recently-sampled selection on the **same synthetic world seed** over 32 decisions per episode. Report mean directly observed discoveries and descriptive neural-minus-scripted differences. These are NOT real Minecraft outcomes and are not used to train or deploy the Forge model.

## Safety and scientific boundaries

- Synthetic hidden transition counts are privileged **simulator diagnostics only**, never model observations or an oracle-derived reward.
- Model update reward is solely a synthetic selected-source discovery indicator minus the same fixed observation cost, without reward labels for unseen alternatives.
- The evaluation is not an off-policy estimate from real Minecraft citizen journals.
- No LLMs, in-game learning, model weight promotion, movement, hauling, crafting or new task authority.
- This single training-seed benchmark is preliminary; later work must add multiple independent training seeds, confidence intervals, pre-registered acceptance thresholds and held-out high-contention real Forge evaluation without data leakage.

A separate lightweight GitHub Actions workflow executes deterministic safety tests, runs the held-out simulator-only benchmark and archives its result. It does not modify the dedicated server workflow or change the pending PR #160 CI run.

## Next gate

Only consider a new frozen candidate model **after** the high-contention Forge benchmark provides a valid reference and after the simulator curriculum demonstrates a robust advantage across independently seeded held-out regimes. Promotion requires fresh Python/Java parity fixtures, an opt-in real Forge canary and run-level comparison against both the frozen neural model and scripted control.
