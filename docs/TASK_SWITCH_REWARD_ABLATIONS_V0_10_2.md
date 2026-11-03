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
