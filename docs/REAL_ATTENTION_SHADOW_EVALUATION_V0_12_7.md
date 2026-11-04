# Hearthbound v0.12.7 — Offline attention shadow over real Forge evidence

This milestone stacks on PR #147 and reads only finalized, previously exported **real Forge citizen choice/outcome** records. It introduces no Minecraft command dispatch, source registrations, or neural action authorization.

## Compared policies

1. `simulator_trained_mlp`: train the frozen 16→16→4 attention MLP from scratch on the abstract synthetic environment (seed 11, 500 episodes); apply it **read-only** to actual Forge *pre-decision* source histories. It has not trained on real Minecraft runs. A 100-tick observation-age transfer scaling is explicitly marked UNVALIDATED.
2. `unknown_first_then_oldest`: prioritize previously uninspected sources, then oldest observed history. This is an observation-only heuristic, **not** the Forge scheduler's true last-*attempt* rotation (which also remembers failed inspections).
3. `first_registered`: choose the first registered candidate by captured source order. Simple deterministic control.

The recorded Forge scheduler remains `LEAST_RECENTLY_SAMPLED`, with actual selected source and observed-or-unobserved result. For each policy the evaluator records recommendation, agreement/disagreement with the recorded selection, selected-outcome coverage only on agreements, and unknown alternative count on disagreements. A disagreement is **not** scored as a success or failure, because the unselected source's contents were never inspected at that tick.

## Safety and analysis boundaries

- Source data must declare `origin=VERIFIED_REAL_FORGE_ATTENTION_JOURNAL`, finalized run provenance and no inferred training labels or execution authority.
- Each decision must maintain contiguous event sequence, nondecreasing server ticks, bounded unique candidate list and a recorded selection within it.
- Any input containing an optimal-action label, fabricated counterfactual reward or known unselected outcomes is rejected.
- Pre-decision model features are built only from directly observed personal resource history: unknown status, last observed availability, observation age and empirical change frequency. There is no true resource volatility or hidden inventory input.
- No policy rewards, regrets, counterfactual rankings or improvement percentages are computed. **Agreement measures what the shadow policy recommends, not whether it would have been better.**
- A single finalized run is never split by event for held-out evaluation. Run IDs are the split unit; these scripts currently describe within-run agreement, not learned generalization.

## Real Forge acceptance

Both dedicated-server CI arms export actual finalized citizen experience before and after restart. The offline shadow evaluator runs on both and its reports must match exactly. Standalone tests cover reproducibility, rejection of unauthorized metadata, prevention of future-state leakage and mandatory abstention on unobserved alternatives.

Artifact: `real-attention-shadow-before-restart.json` and `real-attention-shadow-after-restart.json`.

## Next milestone

Capture several independent finalized Minecraft run IDs with different world seeds and registered source schedules, then evaluate agreement and selected-outcome coverage by **run**, never treating correlated consecutive decisions as independent trials. Measure instrumentation overhead and add explicit choice propensities if future off-policy methods require them. No learned controller should be enabled on the basis of agreement alone.
