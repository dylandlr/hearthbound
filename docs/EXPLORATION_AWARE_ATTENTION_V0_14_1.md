# Hearthbound v0.14.1 — Exploration-aware causal attention research

## Motivation

The real Forge two-chest experiments established actual neural-selected inspections, but both neural and scripted attention witnessed all six source changes in every one of three configured seed pairs. Scripted selection was faster in the small fixed geometry. A separate rapid four-source dedicated-server challenge (PR #160) is being validated. Offline rapid-attention training (PR #161) showed that specializing toward unequal source volatility can improve synthetic discoveries in that regime while worsening others.

**No valid reason exists to replace the frozen real Forge model yet.** The next candidate needs to balance the exploration of unvisited sources with the exploitation of sources known to change.

## Experiment

`scripts/benchmark_exploration_aware_attention.py` trains three neural strategies independently for each of three training seeds (11, 17, 23):

1. **Legacy-style MLP:** in-distribution slow dynamics.
2. **Mixed rapid curriculum MLP:** three training regimes and 1/2/4 hidden source updates per inspection.
3. **Exploration-aware MLP:** the same mixed rapid curriculum plus two *selected-source only* learning incentives: +0.35 when the source had never been inspected before, and +0.12 when the selected source's remembered observation is at least 12 synthetic decisions old.

Each candidate has the same 16→16→4 MLP architecture, the same number of training episodes, and exactly one source observation per decision. The fourth input feature uses *empirical changes in an agent's own direct observations*, **not** the simulator's true hidden volatility.

Every trained candidate is compared to scripted least-recently-sampled selection across four held-out dynamics regimes (in-distribution, low volatility, unequal volatility, high volatility) and three rates (1, 2, 4 hidden updates between inspections). Each seed/regime/rate group gets 40 synthetic held-out episodes of 32 observations. Metrics include directly observed discoveries, mean number of unique sources inspected, minimum visits to any source, and matched initial-seed neural-minus-scripted outcomes.

Simulator trajectories can diverge after different policies choose different source inspections; matching initial random seeds does not ensure identical hidden world histories. Results are **descriptive synthetic benchmarks**, not proof of causal advantage inside real Minecraft. Training and evaluation use disjoint seed namespaces.

## Safety gates

- No direct resource truth, actual source volatility, unselected observations, or invented counterfactual labels enter the policy.
- Only the selected source's observed outcome and *the policy's prior history* contribute to training reward.
- World-level hidden transitions remain offline simulator state; they are not presented as sensor features.
- The real Minecraft model file, Java scorer, four-source challenge and prior results are untouched.
- No online learning, LLMs, navigation, crafting, hauling or task-execution authority.
- `model_promotion_authorized=false` regardless of simulator results.

The separate CI workflow `exploration-aware-attention.yml` runs deterministic causal-history tests and archives the three-training-seed held-out benchmark.

## Decision gate after CI

Report mean per-regime discovery deltas and visit diversity for all three seeds; inspect trade-offs rather than selecting the highest aggregate score. Only propose a new freeze-and-export process if the exploration-aware candidate demonstrates stable held-out behavior across multiple seeds, and only evaluate a new model on real Forge after the rapid four-source control challenge is fully validated. Before live deployment we still need production Python/Java parity, pre-registered admission thresholds and an independent real Minecraft A/B evaluation.

## Worst-regime evidence audit (added after initial draft)

`scripts/report_exploration_attention_tradeoffs.py` independently validates the SHA-256 and every cell of the full three-training-seed × four-regime × three-update-rate matrix. It requires the recorded neural-minus-scripted difference to match reported directly observed discovery counts, and rejects missing/duplicate seed-regime-rate cells or inconsistent better/worse/tied episode counts. The summary reports per-regime average and *worst seed-rate result*, plus the number of negative cases for each learned policy. This makes any specialization/regression trade-off explicit. The workflow archives the verified `exploration-tradeoffs.json` alongside the raw experiment matrix. This audit cannot promote or deploy a neural model, regardless of results.
