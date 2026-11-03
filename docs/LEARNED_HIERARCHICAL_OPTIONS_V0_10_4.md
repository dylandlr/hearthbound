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
