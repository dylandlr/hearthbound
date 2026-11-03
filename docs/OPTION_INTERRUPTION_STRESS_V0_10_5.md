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

## Initial completed benchmark — 2026-11-03

[GitHub Actions run 41712470798](https://github.com/dylandlr/hearthbound/actions/runs/41712470798) passed all clean-run parity, safety, provenance and stress-matrix checks. Each profile has **450 held-out simulated episodes per policy** (3 training seeds × 5 source scenarios × 30 episode seeds). All five profiles together have **2,250 simulated episodes per policy**.

These are equally weighted scenario-averaged task-success percentages for each profile:

| Synthetic stress profile | Learned options | Engineered memory | Scripted reference | Frozen primitive neural | Learned safety-supervisor rejections |
|---|---:|---:|---:|---:|---:|
| Clean long (28 steps) | 94.67% | 94.22% | 94.22% | 73.78% | 0 |
| Two-step delay (28 steps) | 86.45% | 80.00% | 80.00% | 58.44% | 563 |
| Four-step delay (28 steps) | 82.67% | 74.22% | 74.22% | 53.33% | 1,353 |
| Interrupt every fourth step (28 steps) | 93.11% | 91.78% | 91.78% | 75.33% | 0 |
| Three-step delay + interrupt (42 steps) | 96.44% | 92.67% | 89.56% | 72.22% | 919 |

**Interpretation:** The learned controller remained at or above both reference planners on these particular synthetic stress profiles. The increased horizon in the delayed+interrupted case makes cross-profile success comparisons non-causal; that profile gets up to 42 decisions instead of 28. Neither the tiny clean-run advantage nor the larger apparent delay advantage warrants a real-world superiority claim from only three training seeds.

**Critical safety finding:** the learned policy made **563**, **1,353**, and **919** action proposals that a separate current-state supervisor rejected across the three delayed profiles, respectively. They were not executed; the supervisor substituted WAIT. Thus a high success rate is not equivalent to safe independent operation. The stress model's protection depends on this engineered supervisor. The result motivates explicit observation-age features, uncertainty calibration and action confirmation before any Minecraft task dispatch.

The zero-delay 14-step parity suite matched v0.10.4 task outcomes and rewards exactly, ensuring the stress harness did not silently rewrite the earlier benchmark. The stress controller weights were frozen throughout evaluation. This is **SIMULATED_ONLY**, not a Minecraft run, and all recorded interrupts and delayed events are synthetic.

### Next development decision

Before recurrent networks or Minecraft rollout, implement a strict stale-observation handling policy and report two separate metrics: (1) task success after safety-supervisor intervention and (2) **unintervened valid-action rate**. Test whether an age-aware learned option controller avoids proposing unsafe actions without depending on rejections. Preserve both the v0.10.4 checkpoint and this stress benchmark as controls.
