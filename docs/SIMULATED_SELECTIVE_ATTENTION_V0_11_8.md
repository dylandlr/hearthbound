# Hearthbound v0.11.8 — Simulator-only learned attention benchmark

This milestone does **not** deploy the neural model into Minecraft. It establishes a controlled research harness with explicit one-inspection-per-decision budgets and a frozen scripted least-recently-inspected baseline. It stacks on PR #138, which remains authoritative for live Forge monitoring.

## Environment and observed state

Four abstract sources, each with an independently simulated stochastic availability bit. At every decision, the policy receives four features per source: unknown memory flag, previously observed available flag, normalized observation age, and a hypothetical source volatility factor. The simulator's current hidden availability bits are excluded from the model input. The volatility feature is simulator-provided and must be replaced by learned/estimated history statistics before real deployment.

One source inspection is permitted per step. The simulator reveals its availability only after the selected inspection. A change or new observation yields an information reward of 1, otherwise 0, with a fixed inspection cost of 0.04. This is a **proxy information reward**, not verified Minecraft task utility or material profit.

## Compared methods

- SCRIPTED baseline: choose the least recently inspected source with deterministic ties.
- TRAINED_MLP: 16 input / 16 hidden ReLU / four Q-value outputs. Online exploratory reward regression via SGD, epsilon annealing, no LLM or imitation labels.
- UNTRAINED_MLP: frozen untrained comparator.

Training uses distinct deterministic seeds from held-out evaluation. All policies receive 32 inspection opportunities per held-out episode, and the same held-out seed list. The JSON report contains source label SIMULATED_ONLY, separate policy metrics, seed, model dimensions, SHA-256 integrity hash and explicit no-deployment flags.

## Commands

```bash
python3 scripts/test_train_simulated_attention_mlp.py
python3 scripts/train_simulated_attention_mlp.py --seed 11 --episodes 500 --heldout 120 --output simulated-attention-benchmark.json
```

## Acceptance and limits

CI must prove determinism, exclusion of hidden world truth from features, valid one-source choices, and no authorized Minecraft actions. The benchmark only establishes a first trainable comparison; it is not evidence of superiority until evaluation results are measured. Comparing to real Forge should initially be OFFLINE shadow replay over server observations with strict chronology, then operator-controlled canary inspection trials only after safety and performance review. Do not use synthetic performance to claim self-directed Minecraft learning.

Subsequent research should replace the exogenous volatility feature with citizen historical uncertainty estimates, add exploration/regret analysis and per-seed uncertainty intervals, then test for distribution shift to unseen source count, resource volatility, and delayed observations.

## First reproducible evaluation (GitHub Actions run 41746864031)

The independent simulated-attention CI job completed successfully and printed `SIMULATED_ATTENTION_TESTS_PASS`. Configuration: seed 11, 500 simulated training episodes, 120 disjoint held-out episodes, 32 inspection decisions per held-out episode.

| Policy | Mean discoveries | Mean reward |
|---|---:|---:|
| Scripted least recent | 15.81667 | 14.53667 |
| Trained MLP | 15.64167 | 14.36167 |
| Untrained MLP | 9.02500 | 7.74500 |

The trained network exceeded the untrained model but fell short of the scripted baseline by 0.175 discoveries per episode. This **does not** establish statistical significance or evidence of real-Minecraft performance. The immediate next benchmark should use multiple independent training seeds, paired per-seed differences, uncertainty intervals and distribution-shift tests without modifying the original baseline. Do not tune against the held-out set from this run.
