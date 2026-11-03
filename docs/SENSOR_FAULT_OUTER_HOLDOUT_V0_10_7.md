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

## Initial completed outer-holdout results — 2026-11-03

[GitHub Actions run 41716635498](https://github.com/dylandlr/hearthbound/actions/runs/41716635498) completed successfully after the contract test surfaced and we corrected a key task-safety bug: source-observation masks alone do not establish that wheat remains in the inventory at execution time. The independent supervisor now checks actual available source quantities (without disclosing them to the neural policy) before allowing a proposed haul. This was a **real defect in the simulation execution preflight exposed by synthetic inventory drift**, not evidence of an actual Minecraft exploit.

Each profile contains 360 synthetic held-out episodes **per policy** (3 train seeds × 5 source regimes × 24 episode seeds). Outcomes:

| Novel synthetic fault profile | Unrestricted age-aware success | Budget-limited age-aware success | Frozen legacy success | Unrestricted rejections | Budgeted rejections | Legacy rejections | Unrestricted refreshes | Budgeted refreshes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Failed refreshes | 94.44% | 70.00% | 88.89% | 292 | 371 | 1,410 | 1,990 | 991 |
| Hard refresh limit | 97.22% | 68.06% | 85.00% | 0 | 68 | 1,624 | 1,274 | 528 |
| Inventory drift | 96.39% | 68.89% | 74.44% | 259 | 308 | 2,129 | 1,480 | 800 |
| Combined faults | 90.28% | 41.94% | 78.33% | 440 | 465 | 2,334 | 2,958 | 862 |

Interpretation: **unrestricted age-aware sensing is robust in this model, but the same neural network with externally capped refreshes is substantially worse**. The budgeted variant was not retrained to optimize its observation budget: it repeatedly requests refreshes that the executor denies. Consequently the comparison does not establish that an optimally trained budget-conscious policy would perform poorly. It instead shows the existing age-aware model is *not* a good policy under constrained sensing.

Unrestricted refresh counts total **7,702** across the four profiles; this frequency is probably impractical if each refresh translates to a real Minecraft sensor/network operation. Safety rejections also persist (991 for unrestricted age-aware over the nonzero-rejection profiles), so stale-action protection remains necessary. Zero executed invalid tasks depends on the engineered supervisor's current-world preflight, which was tightened after the initial failing CI test.

### Next research decision

Freeze the v0.10.7 outcome and train an explicitly **budget-conditioned** high-level controller. Its observation should include remaining refresh budget, recent refresh success/failure and age of its last *successful* sensor read. Training should include a per-refresh cost and occasional refresh failures, then use a new outer test family with different delay/failure distributions. Evaluate completed primary goals jointly with total refresh cost, rejected proposals, worker latency and colony/personal returns. Do not remove execution-time source validation when later porting decisions to Forge.

This is a negative generalization result for the current age-aware policy under resource constraints, **not a Minecraft gameplay result**.
