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
