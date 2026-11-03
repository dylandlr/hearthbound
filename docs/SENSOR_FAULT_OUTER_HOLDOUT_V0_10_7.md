# Hearthbound v0.10.7 — Sensor failure and information budgets

## Research question

The v0.10.6 age-aware controller completed 90.22% / 94.00% of tasks under 2- and 4-step delayed observations (vs. 86.45% / 82.67% for the frozen legacy control), with zero supervisor rejections. But it used **1,154 and 1,555 sensor refresh requests**, respectively, across 450 synthetic episodes per delay profile. This raises a key concern: are agents learning robust information management, or exploiting an idealized free-to-succeed sensor refresh operation that costs only a tick?

## Preregistered outer holdout

The new experiment freezes all model weights and evaluates **four unseen synthetic fault profiles** that differ from the sensor-delay parameters used in training.

| Profile | Max decisions | Sensor delay | New disturbances |
|---|---:|---:|---|
| Refresh failures | 35 | 5 | Deterministic per-seed/tick 50% refresh failure, budget 4 |
| Limited refresh | 35 | 6 | Strict budget 2, all refreshes succeed |
| Inventory drift | 35 | 5 | Hidden primary-source stock changes every fifth step, budget 4 |
| Combined faults | 49 | 7 | 50% refresh failure, inventory drift every seventh step, interruption every sixth step, budget 3 |

Three arms use the **same environment seeds, fault tick schedules, and original reward contract**: frozen age-aware learned Q, the same age-aware Q with a hard externally enforced refresh budget, and frozen legacy option Q. The budgeted arm is **not** a separately trained neural policy; it is a safety/operational constraint applied to the same network.

Three training seeds × four profiles × five resource scenarios × 24 held-out episode seeds yields **1,440 synthetic episodes per arm**. These are new episode seeds, with unseen *fault parameterizations*, not independent evidence of Minecraft transfer.

## Explicit failure and safety semantics

REFRESH_SENSORS consumes an actual simulated WAIT step. A failed refresh discards the promised fresh post-step observation, leaving the delayed queue to supply the next observation. A budget-denied refresh becomes WAIT without a privileged read. Inventory drift mutates the hidden simulated resource state after an action step, not an already issued observation. Fault schedules are deterministic from episode seed and absolute tick (not dependent on a policy's random calls). The independent supervisor is the *only* component permitted to inspect current action validity; rejected proposals execute WAIT instead.

Output metrics include actual simulated flour outcomes, separate colony and personal rewards, valid-proposal rate, supervisor intervention count, sensor-refresh attempts, executed refreshes, refresh failures, budget denials, hidden inventory changes, episode duration, and trace receipts with redacted hidden inventory.

## Acceptance and research interpretation

A passing workflow proves only contract consistency and deterministic execution. Favor interventions and success jointly; an unbudgeted policy that obtains good results by refreshing every few ticks may be operationally impractical. Failure under novel refresh errors would argue for improved temporal memory, uncertainty and learnable termination, not automatic live deployment.

This is **SIMULATED_ONLY** and adds no Minecraft controls, LLM integration, new biological/social agents or real sensor-reading capability. The previously working Forge/Create dedicated-server smoke remains the authoritative separate game integration gate.
