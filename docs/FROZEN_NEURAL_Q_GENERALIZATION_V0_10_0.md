# Hearthbound v0.10.0 — Frozen neural Q generalization audit

## Why this milestone exists

v0.9.8 achieved 3/3 distinct read-only source-state matches on archived real Minecraft observations. v0.9.9 added unpowered/output-ready machine-context acceptance tests and a fail-closed context gate. The recent Create Maven TLS certificate expiry prevented fresh Forge integration, although the standalone neural and evidence tests remained green.

This milestone tests a different question: **does the simulator-trained policy remain useful beyond the single simulator configuration used during training?** We do not silently retrain the policy on the stress cases and we do not claim the simulation resembles Minecraft's complete dynamics.

## Reproducible design

Three independent reward-trained neural Q models use training seeds **11, 13, 17**, 300 simulator episodes each. All models are frozen before evaluation; checkpoint hashes are asserted unchanged after the complete stress matrix.

Each model is evaluated on **80 independently seeded episodes per scenario**, using separate evaluation seed spaces and the same seeds across the neural, scripted and untrained controls. Five deliberately different simulated resource regimes:

| Scenario | Initial wheat probability | Restock chance per wait action | Decision horizon |
|---|---:|---:|---:|
| Nominal | 45% | 30% | 16 |
| Scarce | 15% | 5% | 16 |
| No restock | 15% | 0% | 16 |
| Abundant | 80% | 80% | 16 |
| Short horizon | 45% | 30% | 5 |

These are **assumptions for an abstract fast simulator**, not measurements of Minecraft wheat availability. Success, timeouts, invalid hauling attempts, policy-gate mismatches, steps, personal and colony rewards are reported separately. Task rewards are simulated, not the verified actual Minecraft reward ledger.

## Out-of-distribution machine states

The 10→20→3 simulator-trained network has no actions for unpowered mills, flour collection, blocked mills, occupied jobs or active processing. Separate representative v2 observation tensors test six conditions: unpowered, output_ready, blocked, busy, processing and stale_source. The frozen neural model always generates a raw Q argmax, but the independent reference safety gate must return **ABSTAIN**. These are synthetic input probes, not claims of real observations or executed neural actions.

## Acceptance and limitations

The CLI explicitly labels both training and evaluation as `SIMULATED_ONLY`, sets `actual_minecraft_worlds=0`, and forbids model promotion. The new CI verifies deterministic seeds, checkpoint immutability, exact train/evaluation counts, separate personal/colony returns and universal abstention on unsupported states. No scripted imitation labels are supplied for neural training.

Performance differences are not statistically generalizable with three models and 80 episodes per stress regime. A network matching the reference in nominal conditions may fail under scarcity or limited decision horizons. **Report failures and negative results, not only successes.**

The next real-world priority is still reliable Forge dependency resolution followed by multiple **real** world seeds and time-sequenced observations with credible action outcomes. This benchmark only establishes simulator stress behavior.

## Initial CI findings (frozen checkpoint matrix)

The first GitHub Actions workflow succeeded. Each cell below represents 80 held-out simulated episodes per model, with three independently trained models. Across model seeds 11/13/17, the neural and scripted mean success rates were:

| Scenario | Neural Q | Scripted | Untrained (context only) |
|---|---:|---:|---:|
| Nominal | 97.92% | 97.92% | 12.5% |
| Scarce | 47.92% | 45.83% | 6.25% |
| No restock | 16.25% | 16.25% | 6.67% |
| Abundant | 100% | 100% | 26.25% |
| Short horizon | 73.75% | 73.75% | 14.17% |

The apparent 2.09 percentage-point scarce-regime advantage is concentrated in one model seed (17); it is **not** sufficient evidence of superiority and should not be promoted as such. In the no-restock regime most worlds cannot succeed because the simulator does not give the citizen any action to produce wheat. These results identify an **action-space and environment-design bottleneck**, not necessarily a model-capacity problem. Raw metrics include per-arm invalid requests and reward breakdowns.

The six machine-context probes per model (unpowered, output-ready, blocked, busy, processing, stale source) all required safety-gate abstention. They were **synthetic observation probes**; they did not execute jobs or control live Minecraft.

The successful CI artifact is the authoritative machine-readable result; the table above is an informal arithmetic mean across three model seeds, not a confidence interval.
