# Hearthbound v0.10.4 — Learning to choose and switch task options

## Verified predecessor and hypothesis

v0.10.3's engineered goal memory matched the scripted reference at 83.89% versus 67.50% for its underlying neural Q network over 720 held-out simulated episodes. But those improvements came from *hand-written option transitions*. The next experiment asks if a neural controller can learn to select and switch between task options from reward, without inheriting that transition schedule.

## New, genuinely trainable high-level network

The trainable controller is a separate 19→24→3 neural Q model. Its high-level inputs are the 15-feature bounded resource-task observations, three one-hot indicators for the previous selected option, and one flag for an observed secondary-job completion event. It never reads true hidden source stock. It chooses among `SEEK_WHEAT`, `SECONDARY_JOB` and `WAIT` using trained temporal-difference values. On each decision, it can continue the previous option or switch to another based on its learned Q-values; no hand-coded forced transition after secondary-job completion is used.

The *execution of an option remains hand-designed*: `SEEK_WHEAT` inspects unknown sources or hauls from an observed stocked source using the frozen low-level goal-bonus Q model to choose among legal primitives. `SECONDARY_JOB` performs the legal alternate job and `WAIT` waits. Option applicability masks prevent impossible jobs or hauling from unknown/empty sources. No controller can issue actual Minecraft commands.

The high-level network optimizes the **original** combined colony+personal simulated reward, not an invented return-to-goal bonus, with experience replay, a lagged target Q network, and epsilon-greedy exploration. It is **not** an RNN/LSTM/GRU, learned primitive skill, full option-critic architecture, or independently discovered task ontology.

## Four matched evaluation arms

For each training seed 11, 13, 17, first recreate the exact v0.10.2 frozen low-level goal-bonus neural checkpoint with 350 simulated training episodes. Train a new upper-level Q network from scratch with 480 separate simulation episodes. Evaluate on six held-out regimes using the exact same episode-seed allocation and original simulated rewards as earlier benchmarks:

1. `learned_options`: trainable upper-level option selection with previous-option/event memory over frozen low-level Q.
2. `frozen_neural`: unmodified goal-bonus neural primitive policy.
3. `engineered_memory`: v0.10.3 hand-designed option scheduler over the same frozen neural primitive policy.
4. `scripted`: original pure rule-based primitive controller.

Each policy receives 40 held-out episodes per scenario per training seed (720 simulated episodes per policy). Report independent flour outcomes, secondary jobs, option switches, post-secondary resumptions, personal/colony rewards, invalid actions, and one ordered event trace for each scenario/seed.

The low-level and meta checkpoints are checked for zero changes after evaluation. Tests require true TD learning updates, actual option switching and task completion observation, source masks, reproducibility and parity with the earlier engineered baseline.

## Claims and acceptance

A test that merely executes the trainer is not sufficient: review held-out performance, variance between training seeds and whether option choices become stuck in secondary jobs or waiting. A learned controller that is inferior to the engineered scheduler is a negative result, not autonomous intelligence. The simulator remains synthetic and cannot justify model deployment.

All trained options and execution remain **SIMULATED_ONLY**. The game mod's ten-feature v2 neural contract and previous Forge policy selector stay untouched. No LLMs, Minecraft neural controller, persistent Minecraft citizen memory, or recurrent neural network are added by this PR.

## Next phase

If the learned controller proves limited, investigate learned temporally extended options (semi-Markov updates/option-critic termination), longer recurrent memory, and goal-conditioned policy training. Larger genuinely held-out real Minecraft scenarios, delayed task completion, and multiple citizens remain necessary for claims about colony-wide planning.

## First completed CI results — November 3, 2026

Standalone learned-option CI [run 41710612846](https://github.com/dylandlr/hearthbound/actions/runs/41710612846) passed, including genuine TD gradient checks, the observed-event/previous-option memory contract, no-masked-action assertions, parity with the frozen comparator, and complete held-out matrix.

All four policy arms were evaluated on the same **720 simulated episodes each** (3 training seeds × 6 scenarios × 40 held-out episode seeds):

| Policy | Mean simulated flour success |
|---|---:|
| Frozen low-level neural only | 67.50% |
| Engineered v0.10.3 goal-memory overlay | 83.89% |
| Scripted reference | 83.89% |
| **Learned high-level option Q controller** | **84.86%** |

The learned meta-controller improved flour success by **17.36 percentage points** against the frozen primitive neural control, but by just **0.97 points** against the engineered/scripted scheduling controls. This exploratory difference is too small and training-seed-dependent to claim statistical superiority. It generated **1,899 option switches** across the evaluation matrix; option switches themselves are not evidence of progress and may signal over-switching in longer sequences.

Representative per-seed differences reveal why we must not treat the 84.86% aggregate as a victory. In the `both_empty` scenario, learned option success was 45%, 52.5%, 62.5% across the three training seeds versus 50%, 50%, 52.5% scripted; in `alternate_empty` it was 70%, 82.5%, 82.5% versus 72.5%, 80%, 72.5%. The learned controller did not uniformly beat the rules.

The neural upper-level option choice and switching are **genuinely reward-trained**, using a separate 19→24→3 Q network. However, lower-level option executors and action masks are still engineered, memory is short explicit state rather than trained recurrence, and all transitions are synthetic. No new policy was installed in Minecraft. The scientific result is proof that a learned upper-level scheduler can *approach* the hand-designed baseline in this constrained simulator.

### Decision

Preserve v0.10.4 network IDs and full reward/event traces. Next, evaluate option-selection stability under longer horizons, observation delays, spontaneous interruptions and unseen supply distributions. Introduce an explicit learned option-termination objective or recurrent state representation if these tests show short-memory failure, without changing evaluation rewards or selecting on the held-out test set.
