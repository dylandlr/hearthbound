# Hearthbound v0.14.9 — Frozen-forecaster decision rules

## Why this experiment exists

PR #169 trained a recurrent predictor of **source disagreement since the previous direct inspection**, using no unobserved truth or unselected labels. Its initial simulator benchmark passed, improving mean reinspection Brier score versus a smoothed personal-history baseline (**0.2399 vs 0.2505**), but greedy forecast-driven inspection averaged **−0.916 discoveries per 32 decisions** versus scripted rotation, with serious normal/low-volatility regressions. The latest admission-audit and dedicated-server CI results remain independently checked by PR #169; a predictive advantage alone is not an action-policy advantage.

This experiment holds that trained predictor constant and varies only the **decision contract**. It does not retrain per policy or change the existing real Forge model.

## Four precommitted decision rules

- **Scripted:** least-recently-inspected source, retaining the baseline.
- **Greedy forecast:** visit all sources for at least two direct inspections, then choose the greatest predicted probability of changing since its prior observed state.
- **Age-blended forecast:** after at least two direct observations per source, rank candidates by `0.65 × predicted_disagreement + 0.35 × min(age,20)/20`. Younger/older ages are derived from the citizen's own inspection history.
- **Coverage-guarded forecast:** after two direct observations of every source, allow a forecast-driven deviation only when the predicted probability spread is at least `0.20`. Reject a third consecutive *neural-prioritized* selection of the same source in favor of scripted fallback. This is a limit on neural preference, not a guarantee that the resulting scripted action never chooses the same source.

These weights and guards are fixed before evaluating the new held-out matrix. They are not tuned on the prior real Forge source-change outcomes.

## Execution and provenance

For each training seed (11, 17, 23), train **one GRU forecaster** from scratch on 180 simulator episodes using PR #169's behavior policy and only directly witnessed reinspection labels. Freeze its parameters, record a SHA-256 hash of the weights, then replay **all four rules** on the exact same pre-generated 32-step hidden source trajectories in each held-out episode.

Four volatility regimes × three world-update rates × 24 episodes per seed produce 36 seed/regime/rate cells (864 paired synthetic episodes). For each rule report mean direct discoveries, minimum visits to any source, source coverage, deviation frequency from scripted fallback, per-seed and per-regime deltas, and signed trajectory manifests. Forecast inputs and recurrent memory remain agent-specific since choices determine what each agent learns, but frozen source truth and model parameters are identical across arms.

The outcome is **synthetic selected-source discoveries**, not survival, hauling, technology, colony intelligence, or real Minecraft success. Even if the guarded rule beats scripted on some regimes, deployment remains forbidden until multi-seed, multi-regime admission gates and independent real Forge canaries are passed. No LLMs, new Minecraft actions, hidden resource truth, unselected counterfactual rewards, online training, or runtime weight replacement are introduced.

## Interpretation

This tests whether **policy selection** is the source of forecast utility losses. Improvements would justify more systematic decision-rule evaluation, not arbitrary tuning on held-out scores. If all forecast-driven rules still fail, the next step is to reconsider the forecast target and its relationship with expected information gain, not simply enlarge the neural network.

## Initial verified policy-only study (GitHub Actions 42104969036)

The CI benchmark passed and archived 36 seed/regime/rate groups. Compared against scripted rotation, mean *directly witnessed synthetic source disagreements* per 32 decisions were **−0.915509 greedy forecast**, **+0.313657 age-blend forecast**, and **0.000000 coverage guard**.

Per-regime (greedy; age-blend): in-distribution **−2.837963; −0.208333**, low volatility **−3.717593; −0.166667**, unequal volatility **+2.745370; +1.388889**, high volatility **+0.148148; +0.240741**. The age-aware arm averaged positive results across all three training seeds (+0.472222, +0.177083, +0.291667), but had **15 negative seed/regime/rate cells** and negative mean performance in the normal and low-volatility regimes. It has **not** met a robust admission bar.

Critically, the coverage guard made exactly **zero** non-scripted policy choices across all evaluated episodes. Its equal score is an inactive fallback, **not** evidence that a hybrid neural controller outperformed or improved stability. In contrast, the age-blended rule made approximately **11.08** different choices per episode and averaged approximately **5.99 minimum visits per source**, versus scripted's eight. Greedy forecast made approximately **24** deviations per episode but concentrated visits, with mean minimum visits of two.

The independent `report_forecast_policy_admission.py` now checks the signed raw experiment, one frozen model hash per training seed, observed-score consistency and per-seed/per-regime outcomes. It rejects a candidate from exploratory admission if it never deviates from scripted, has a negative per-seed mean or has a negative per-regime mean. **Passing simulator admission would still never authorize Minecraft deployment.**

The next research experiment should test whether age weighting and forecast uncertainty are robust to *new, undisclosed* resource schedules (additional sources, bursty dynamics, short inspection budgets), rather than selecting a tuned constant using these same held-out outcomes.
