# Hearthbound v0.14.8 — Direct-observation GRU forecasting

## Motivation and existing real Minecraft evidence

All six CI workflows of PR #168 passed. With matched optimizer update counts, eight-step BPTT GRU improved synthetic directly witnessed discoveries by roughly **0.080 per 32 decisions** relative to buffered one-step GRU, but both trailed scripted selection overall. The true Forge four-source challenge in PR #160 still favors scripted attention (**8/16** witnessed operator mutations compared with **5/16** for the frozen neural model), one controlled fixture pair only.

The next question is not "can we improve a pooled selection score by changing its reward?" but whether the citizen's own observation history contains **predictive temporal information**, and whether calibrated forecasts actually lead to better inspections.

## Training target and causal boundary

`scripts/benchmark_observed_change_forecast.py` uses the same 22→12→4 GRU architecture and eight-step truncated BPTT. The source-selection outputs are interpreted as four Bernoulli logits predicting whether each source differs from its **own most recently directly observed state** at the next inspection.

Only the selected source is observed. First inspection of a source establishes a baseline and has **no supervised change label**. A subsequent direct inspection yields one binary label: source changed since its previous direct inspection or did not change. Training uses masked binary cross-entropy for that selected label only. Crucially, labels for unselected sources are absent even though the simulator generates their hidden trajectories. The gradient checks verify the loss through all recurrent gates and that an all-masked sequence gives a zero update.

A training citizen follows scripted least-recent inspection with 20% seeded random probes. This behavior policy is independent of the forecast, reducing selection-feedback confounding when measuring predictive accuracy. All simulated source changes are pre-generated and shared between evaluated arms.

## Two independent tests

**1. Forecast quality (fixed probe distribution).** On held-out trajectories, replay a frozen exogenous probe policy while recording GRU probabilities only on directly observed *reinspections*. Compare Brier score with a smoothed per-source historical disagreement-rate baseline calculated from the same citizen's direct observations, and report five confidence/reliability bins. Never grade uninspected source logits or first-inspection events against latent truth.

**2. Attention utility (interactive policy).** On the same hidden trajectory, compare scripted rotation with a policy that visits each source at least twice before using the highest predicted change probability. Log directly witnessed changes and minimum per-source visits. Evaluation policy choices can affect the GRU's own observation histories, but not the pre-generated environment trajectory.

For each of training seeds 11, 17, 23, evaluate four source-volatility regimes × three latent-update rates × 24 held-out episodes. Reports retain per-cell world hashes, supervised label counts, Brier scores, calibration bins, and selected-discovery differences.

## Interpretation and safety

Forecast accuracy and action utility are intentionally separated: good Brier score need not improve selected-source decisions, and a high average discovery score need not imply calibrated forecasts. Unobserved changes that occur and revert between visits are not distinguishable in the binary target; the model predicts **observed disagreement at the next direct inspection**, not latent event occurrence or true per-tick volatility.

This is an exploratory **simulator-only** study. No new weights are deployed to Forge, no personal Minecraft data are used to train, and no privileged source states, counterfactual labels, LLMs, movement, crafting, hauling, or new task authority are introduced. Promotion remains forbidden regardless of results. Any later live experiment requires source-event parity checks, an independently held-out real Forge challenge and multi-run replication.

## Initial independent CI result and admission decision

The corrected GRU forecasting benchmark passed in GitHub Actions run [42103467860](https://github.com/dylandlr/hearthbound/actions/runs/42103467860). The GRU improved **mean Brier score** on directly inspected, held-out reinspection cases from **0.25053** (smoothed observed-history baseline) to **0.23988**. This is a descriptive improvement, not a significance claim. The same forecast-driven selection policy still averaged **−0.91551 directly witnessed changes per 32-decision episode** versus scripted rotation, with negative mean policy scores on **all three training seeds**.

By regime, GRU Brier vs observed-history Brier; forecast-policy discovery difference vs scripted:
- In distribution: 0.24891 vs 0.26787; **−2.83796**.
- Low volatility: 0.23273 vs 0.22814; **−3.71759**.
- Unequal volatility: 0.22810 vs 0.23610; **+2.74537**.
- High volatility: 0.24977 vs 0.27003; **+0.14815**.

Each regime's 9 seed/rate cells contained **6,048 directly observed reinspection forecast labels** in aggregate. No hidden resource states were scored as if they were directly observed.

An independently signed `report_observed_change_admission.py` now checks the canonical 36-cell evidence, validates direct-discovery and calibration counts, and reports prediction improvement and decision performance separately. Simulator admission requires better average Brier score **and** nonnegative policy performance in every training seed **and** no more than −0.25 average discovery regression in every regime. The current candidate fails admission. Even passage would not authorize Minecraft model deployment.

**Next scientific question:** whether a calibrated forecast combined with an age-aware, coverage-aware decision objective (instead of greedy maximum change probability) reduces normal/low-volatility regressions. Keep the forecast predictor frozen when comparing decision rules, so any difference is due to the policy rather than another simultaneously retrained model.
