# Hearthbound v0.14.2 — History-gated selective attention (simulator only)

## Evidence-driven motivation

The complete dedicated Forge four-resource challenge in PR #160 passed all CI. Real Minecraft server journals recorded 16 operator-changed source states in each arm, 10 actual inspections per citizen and 8 witnessed changes for SCRIPTED versus 5 for the frozen NEURAL model. Those numbers are an observation on one controlled, separately ticking world pair, not a statistically supported superiority claim.

The exploration-aware MLP benchmark in PR #162 also passed. In the full three-training-seed held-out synthetic matrix, exploration-aware training improved discoveries over scripted attention in unequal-volatility regimes by +2.575 discoveries per 32-decision episode (averaged across update rates), but trailed scripted rotation by −1.678 in-distribution and −2.128 in low-volatility conditions. The results justify *evaluating* a history-dependent policy choice, not deploying new neural weights.

## Experimental candidate

Keep all existing scripted, frozen neural and exploration-aware MLP controls. Add a conservative, fixed-threshold **history gate**:

- Use scripted least-recently-sampled selection until the citizen has directly inspected **every registered source at least three times**.
- Permit neural selection only when observed source change frequencies, calculated from the citizen's **own** direct observation history, have a maximum-minus-minimum spread of at least **0.40**.
- Limit learned selection bursts to **two consecutive choices**, then return to scripted selection at least once.
- Otherwise fall back to unchanged scripted rotation.

These constants were precommitted before the next 36-case held-out run. They are not selected from real Forge results, held-out evaluation performance, or hidden resource truth. They are conservative experimental settings, not a validated optimum.

An episode has exactly one source inspection each decision, regardless of which policy controls attention. Training continues to use only the selected resource observation, with the same 16→16→4 MLP, novelty/revisit shaping and simulator-only hidden transitions. No extra observations, tasks, Minecraft actions or resources are granted to the gated policy.

## Evaluation and limitations

For each training seed (11,17,23), train an exploration-aware MLP from scratch. Evaluate three selectors on the same initial synthetic seed across all 4 volatility regimes × 3 update rates × 40 held-out episodes, with 32 decisions per episode:

1. Scripted rotation.
2. Always-on exploration-aware neural attention.
3. The conservative history-gated exploration-aware neural attention.

Archive per-seed/regime/rate direct discoveries, mean number of gated neural decisions and minimum visits to any source, plus per-regime mean and number of negative cases against scripted selection. The policies' later stochastic histories may diverge, so identical initial seeds are not claimed to be identical tick-level trajectories.

The main hypotheses to test are whether the gate reduces losses on stable/low-volatility resources and whether it preserves any gains on unequal-volatility sources. There is **no promise** that both objectives can be achieved.

## Execution authority and promotion barriers

The study is synthetic only, in a separate lightweight GitHub Actions workflow. It does not load a new model into real Forge, change the server resource schedule, train online, or authorize Minecraft navigation, hauling, crafting or task execution. Keep `model_promotion_authorized=false` regardless of benchmark results.

Any later real deployment requires frozen candidate weights, production Java parity, explicit operator opt-in, a fully verified Forge source-choice journal, matched run-level evaluation with the scripted and original frozen neural controls, and held-out environment replication.

No LLMs are introduced.
