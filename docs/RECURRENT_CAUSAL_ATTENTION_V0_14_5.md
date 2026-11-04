# Hearthbound v0.14.5 — Trainable recurrent attention (simulator only)

## Goal

The frozen-timeline audit in PR #165 passed all CI and confirmed that our previous synthetic result comparisons already had action-independent source transitions. We can now compare sequence memory against scripted rotation and the exploration-aware MLP using *exactly identical* hidden trajectories per evaluation episode.

## Architecture

`scripts/benchmark_recurrent_causal_attention.py` implements a small **GRU** with 22 inputs, 12 recurrent hidden units and 4 source-selection outputs. Input is:

- The same 16 causal per-source history features used by the MLP.
- A four-way one-hot encoding of the **previously selected** source.
- The previous selected observation's discovery flag and availability flag.

The recurrent state persists across decision steps inside an episode and resets at episode boundaries. GRU update, reset and candidate gates all have trainable recurrent matrices. Its loss is squared error between the chosen source score and the selected source's **actually observed synthetic discovery**, with a one-step truncated gradient through the current GRU cell; no backpropagation through earlier hidden states. This is **not full backpropagation through time** or an implementation of a long-range policy-gradient RL objective. The finite-difference regression test independently checks every gate, recurrent weight group, output layer and bias gradient.

## Evaluation

For each training seed (11,17,23), train the GRU and the existing exploration-aware MLP for **180 episodes each**, with 32 selected-source inspections per episode. Compare:

1. Scripted least-recent rotation.
2. Exploration-aware MLP.
3. Recurrent GRU.

Use 4 held-out resource regimes × 3 hidden world update rates × 30 held-out episodes per seed. Every arm in an evaluation episode receives the same pre-generated resource sequence (not merely the same starting seed). Report directly observed source discoveries, least-visited source counts, per-cell differences from scripted, and per-cell trajectory manifest hashes. There are 36 independent training-seed × regime × rate groups, not 36 independent world samples.

## Constraints

Hidden source truth and future timeline are inaccessible until the selected source is inspected. The GRU is trained only from a selected source's actual synthetic outcome. No counterfactual reward is provided for uninspected alternatives. The model is not deployed to Forge, does not read real Forge training journals, and does not gain any task, movement, crafting or hauling authority. No LLMs are used.

This is an exploratory memory test. Its result may be negative. A synthetic performance improvement is not permission to replace the frozen real Forge neural selector, which underperformed scripted rotation in the actual four-source test (5/16 vs 8/16 witnessed changes). Before any future promotion, require independent recurrent robustness tests, production Java numerical parity, deterministic serialization, and real Forge held-out controlled trials.

## Initial real CI benchmark result

GitHub Actions run [41919749455](https://github.com/dylandlr/hearthbound/actions/runs/41919749455) successfully executed the three-seed frozen-timeline GRU benchmark and produced the archived JSON. The 36-cell mean directly observed discovery difference relative to scripted was **−0.47037 for GRU** and **−0.73611 for exploration MLP**, with 180 training episodes each. Per-regime differences (MLP, GRU): in-distribution (−1.8926, −1.5296), low volatility (−2.6111, −2.0593), unequal volatility (+1.6741, +1.9148), and high volatility (−0.1148, −0.2074). The GRU did better than this MLP in three of four regimes but not better than scripted overall.

Per-training-seed GRU-vs-scripted means were approximately −0.2472, −0.5778, and −0.5861, respectively. **All three were negative.** One-step-truncated recurrent training has not established sufficient long-horizon temporal learning to justify runtime promotion.

An additional independent `report_recurrent_attention_admission.py` validates the signed 36-cell source report, reproduces the per-cell direct discovery deltas, rejects tampered or duplicate cells and evaluates seed/regime robustness. It deliberately requires nonnegative performance per training seed and no worse than −0.25 per regime, while setting `model_promotion_authorized=false` regardless of outcome. This initial GRU candidate fails those criteria. The additional CI run is pending.

## Next scientific improvement

Consider full truncated backpropagation-through-time over sequences rather than the current single-step gradient, and evaluate an observation-aware GRU trained to predict **change since last inspection** with calibrated uncertainty. Distinguish forecasting improvements from policy reward improvements; preserve the frozen trajectories and scripted baseline. Do not select architectures by a single synthetic regime.
