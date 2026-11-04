# Hearthbound v0.14.3 — Observed-uncertainty attention objective

## Evidence and rationale

PR #160's real Forge four-source high-contention test verified ten citizen inspections per arm. Scripted attention witnessed **8/16** operator-authored real resource changes; the frozen causal-history MLP witnessed **5/16**. This single independent-run pair does not prove universal superiority, but is evidence that the current live learned selector is weaker on this fixture.

PR #163's synthetic held-out gate achieved a slightly positive pooled discovery delta of about +0.044 per 32-decision episode while regressing on some independent seeds and normal/low-volatility regimes. A separate conservative admission audit explicitly withholds model promotion. The next candidate should not be selected by pooled means alone.

## Objective experiment — SIMULATOR ONLY

Train a new 16-input, 16-hidden, 4-output MLP with one inspected source per decision and a direct selected-source reward, followed by modest regularizing history terms calculated before the inspection:

`r = r_selected_direct + 0.22 * observed_history_uncertainty + 0.08 * capped_age - 0.16 * rapid_reinspect + 0.28 * first_inspection`

The directly observed reward is the synthetic selected-source discovery indicator minus the same fixed inspection cost. `observed_history_uncertainty = 4p(1-p)`, where `p=(observed_differences+1)/(observations-1+2)`. This smoothed Bernoulli quantity measures *disagreement between previous direct inspections*, not the true hazard of a resource changing per tick. It is a training-shaping proxy; its reliability can be poor when resources flip multiple times between visits.

All extra terms come from the citizen's **own memory before the selected observation**. Neither the hidden state of unselected sources nor their counterfactual rewards are available to the learner. The simulator's hidden source transitions only advance the synthetic environment after inspection.

## Baselines and evaluation

Compare (a) scripted least-recent rotation, (b) the exploration-aware MLP from PR #162, (c) the history-gated use of that MLP from PR #163, and (d) the new uncertainty-objective MLP. Train three independent candidates with training seeds 11, 17, and 23. Evaluate 4 volatility regimes × 3 hidden update rates × 40 held-out episodes per seed, each with 32 decision opportunities. Report mean directly observed discoveries, minimum source visits, and neural-minus-scripted discovery differences at **each** seed/regime/rate combination. Training seeds and evaluation seed namespace remain disjoint.

These are matched initial synthetic world seeds, not guarantees that two policies share exactly the same future hidden stochastic trajectories after diverging choices. Do not claim a causal effect, statistical significance, generalized Minecraft intelligence, or real Forge performance.

## Admission and execution boundary

- The four-source Forge challenge is a fixed real-world benchmark. Its outcomes are **not** used to train this objective.
- The previously deployed Java model weights stay frozen; Python/Java model parity and real Forge safety checks continue to apply to existing controls.
- The research workflow evaluates this model without any Minecraft server connection.
- `model_promotion_authorized=false` regardless of performance. Any future model must pass multi-seed robustness gates and an opt-in real Forge A/B evaluation under a new held-out intervention plan.

No LLMs, Minecraft online learning, hauling, crafting, movement, or new task-execution powers are introduced.

## Actual held-out simulator results (GitHub Actions run 41911964690)

The initial 3-training-seed, 36-cell simulator run passed. The archived synthetic report shows uncertainty-aware MLP vs scripted rotation by volatility regime, averaged over seeds and update rates: in-distribution **−0.72778**, low volatility **−0.61111**, unequal volatility **+0.59167**, and high volatility **−0.04167** discoveries per 32-decision episode. The corresponding history-gated candidate from PR #163 achieved **−0.46944**, **−0.58056**, **+1.17500**, and **+0.05000**. The uncertainty-aware objective's pooled mean was **−0.19722**.

Training-seed means for uncertainty-aware were **+0.43750** (seed 11), **−0.19583** (seed 17), and **−0.83333** (seed 23). This is **not** robust across training seeds or ordinary source dynamics. The objective does not merit deployment.

An independent `report_observed_uncertainty_admission.py` now validates the signed 36-cell source report and its direct-observation counts before reporting robustness per seed and per regime. Its conservative rejection thresholds are nonnegative discovery difference for **each** training seed and no worse than −0.25 for **each** volatility regime. The current results fail both gates. Even passing these gates would never authorize Minecraft deployment; production Java parity, a held-out Forge challenge and new independent server-run evaluation remain prerequisites.
