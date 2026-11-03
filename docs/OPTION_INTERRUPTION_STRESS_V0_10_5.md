# Hearthbound v0.10.5 — Learned option robustness under delays and interruptions

## Motivation

The v0.10.4 neural upper-level option controller achieved **84.86%** flour success in a clean, abstract held-out simulator, compared with **83.89%** for the engineered scheduler and scripted planner. That small advantage is not conclusive. Real citizens will face stale inventories, interruptions, delayed work-completion notifications and extended task horizons.

## Protocol

The networks are **retrained only on the unchanged v0.10.4 training environment** to reproduce frozen checkpoints (low-level: goal-bonus Q, 350 episodes per seed; meta-controller: learned-options Q, 480 episodes per seed). No model is trained on stress profiles or held-out results.

Four arms: learned high-level option controller, hand-engineered goal-memory overlay, frozen low-level neural Q alone, and scripted planner. Five synthetic stress conditions:

| Stress profile | Max steps | Observation and event delay | Interruption interval |
|---|---:|---:|---:|
| Clean long | 28 | 0 | none |
| Delay 2 | 28 | 2 decisions | none |
| Delay 4 | 28 | 4 decisions | none |
| Interrupted | 28 | 0 | every fourth decision |
| Delayed + interrupted | 42 | 3 decisions | every fifth decision |

Evaluate five synthetic resource scenarios: standard, primary empty, both empty, alternate empty, supply shift. Each policy receives **30 fixed held-out worlds per scenario/profile/training seed**, with three training seeds 11/13/17, totaling 2,250 simulated evaluations **per policy**.

Sensors and task-completion notifications are queued to create genuine per-policy observation latency. A simulated safety supervisor may check the **current** valid action mask only to reject dangerous stale proposals and substitute WAIT; it never exposes its live inventory values to a policy for action selection. This distinction avoids pretending a stale model can authorize real inventory operations. Interruptions consume an actual simulation decision step and may change world state through an ordinary WAIT action. They are not Minecraft events.

Metrics: flour outcome, secondary-job completion, invalid task requests, supervisor rejections, option switches, returns from secondary work, separate personal and colony rewards, interruption counts and duration. Persist one full event/observation trace per scenario/profile/seed for audit.

## Acceptance and limitations

The zero-latency, 14-step test must reproduce v0.10.4 results exactly with identical checkpoints and world seeds. Unsafe stale proposals must be rejected, never executed. Models are hashed before and after the stress matrix. All data are **SIMULATED_ONLY** with `minecraft_worlds_executed=0` and `minecraft_action_authorized=false`.

This experiment does not train a recurrent neural network and does not establish robustness on real servers. A failure under delays would motivate a trained temporal memory representation, delayed observation handling or explicit option-duration training rather than arbitrary reward changes.

The newly recovered Forge compilation and dedicated-server checks remain independent real-world baselines; this PR does not modify the mod's active policy or execute neural options on Minecraft.
