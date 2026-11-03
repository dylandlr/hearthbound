# Hearthbound v0.10.2 — Task-switch reward ablations (SIMULATED ONLY)

## Hypothesis and frozen baseline

The previous v0.10.1 reward-trained 15→24→6 neural policy often completed the alternate job but fell short of the scripted reference on flour production. This may indicate a poorly weighted intermediate task reward, weak credit assignment, limited episode horizon, or a representation/optimization problem. The experiment is not designed to assume the cause in advance.

The `original` variant must reproduce **exactly** the prior v0.10.1 model hash when trained with the same seed and episode count. The previous results remain preserved; it is an immutable experimental control.

## Four preregistered variants

1. `original`: identical reward and training algorithm to v0.10.1.
2. `goal_bonus`: add +1.0 to the **training TD reward** for actual simulated flour task completion. No synthetic flour is created; other task rewards are unchanged.
3. `secondary_discount`: subtract 0.5 from the **training TD reward** when the alternative job completes. The environment's reported personal and colony rewards remain unchanged.
4. `potential_shaping`: add `gamma * Phi(s_next) - Phi(s)` to the TD reward, with gamma=0.96 and potential=+0.15 for each known available source (terminal potential zero). This is an exploratory reward-shaping baseline, not guaranteed to preserve an optimal policy in this approximate, partially observed learning setup.

All variants share model architecture, initialization seeds, experience replay, exploration schedules, episode budgets, action masks and transition dynamics. **Only their training TD reward differs.**

## Evaluation contract

Three independent training seeds (11,13,17), 350 training episodes per strategy and seed. Each frozen model is evaluated across the same six scenarios as v0.10.1: standard, primary empty, both empty, alternate empty, no secondary job, and supply shift. Each scenario/model uses 40 fixed held-out seeds, matched against every other strategy and the scripted control.

Every evaluation runs the **original unmodified v0.10.1 environment and reward function** regardless of training variant. Reports include per-episode flour success, alternate-job completion, timeouts, steps, invalid requests, per-action counts, personal and colony rewards, and detailed episode seeds. Different policies can consume RNG draws at different times, so matching seeds ensures matched initial conditions, **not necessarily identical exogenous restock sequences**.

Do not select a winner based on only this dataset. Compare effects across independent training seeds, measure the variance and inspect failures and reward tradeoffs. A more explicit colony objective may make auxiliary personal work less attractive; that change must be evaluated separately rather than smuggled into the original evaluation reward.

## CI and scientific limits

CI asserts exact reproduction of the v0.10.1 original network, rewards changing only at the intended training step, frozen model hashes, deterministic reruns, consistent held-out seeds, no masked actions, and zero authorized Minecraft execution.

This is not a Minecraft trial, not evidence of biological or social task-switch learning, and not authorization to update Sable. Fresh Forge/Create integration remains separately blocked by the previously identified upstream TLS certificate expiry.

## Next phase

If any reward variant consistently improves primary task success without sacrificing safety, test additional training budgets/horizons before a new real-world read-only evaluation. Otherwise shift to recurrent memory, explicit task-option termination and scheduling, and collect real multi-source observations before choosing architecture.

## First completed CI results (November 3, 2026)

GitHub Actions reward ablation workflow `41688818522` **completed successfully**, including exact original-model checkpoint reproduction and isolated training-reward checks. There are three training seeds, six evaluation scenarios and 40 held-out simulated worlds per seed and scenario: **720 evaluation episodes per strategy**, plus the separate scripted reference episodes.

These are unweighted means across all 18 (three-seed × six-scenario) cells:

| Evaluation policy | Mean simulated flour success |
|---|---:|
| Scripted reference | **83.89%** |
| Original v0.10.1 neural (reproduced) | 53.89% |
| +1.0 flour completion training bonus | **67.50%** |
| -0.5 secondary job training discount | 59.03% |
| Known-source potential shaping | 57.50% |

The goal bonus improved the mean by **13.61 percentage points** relative to the preserved original neural control, but still trailed the scripted reference by **16.39 points**. Improvements varied by seed, and no reward variant won consistently in every scenario.

Mean simulated flour-success rates for `goal_bonus` by scenario (scripted reference in parentheses):

- Standard: **65.83%** (84.17%)
- Primary empty / alternate stocked: **100%** (100%)
- Both initially empty: **22.50%** (50.83%)
- Alternate empty: **45.83%** (75%)
- No secondary job: **70.83%** (93.33%)
- Supply shift: **100%** (100%)

Important: both-empty worlds can succeed after an exogenous restock in the simulator, but the learned model's outcomes remain less consistent than the scripted policy. Seed-specific overall averages for goal bonus were **55.00%, 70.42%, and 77.08%** (seeds 11, 13, 17); this variability is too large to infer robust superiority.

No model was updated based on held-out results; the benchmark used only the preregistered training rewards. Source artifacts include full action counts, alternate-job outcomes, separate personal and colony rewards, timeouts and matched episode identifiers. The best apparent variant is a **candidate for follow-up**, not a deployed or accepted Minecraft policy.

### Decision

Keep the original and all reward variants frozen. A useful next experiment is an independent, larger outer holdout across new supply distributions and longer job sequences, plus event-timeline inspection of **secondary job → source reinspection → flour**. Do not treat scalar reward tuning as the only explanation: temporal credit assignment, history-dependent observations and goal-conditioned scheduling may matter more. Real Minecraft development remains under the upstream Create Maven certificate blocker.
