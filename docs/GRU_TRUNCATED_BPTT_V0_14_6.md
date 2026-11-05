# Hearthbound v0.14.6 — Eight-step truncated GRU backpropagation

## Baseline and immediate repair

PR #166's original three-seed GRU benchmark passed, but a later independent admission-audit workflow failed because its parser expected `world_updates_per_inspection` while the actual benchmark emits `updates_per_inspection`. The contract was corrected on the base branch in commit `a872390` before creating this research branch. The error was in the admission-report schema field name, **not** the original recurrent-model gradient benchmark.

The original GRU trained with one-step truncated gradients, preventing later selected-source discoveries from changing how earlier observations were retained in recurrent state. The first held-out synthetic benchmark showed mean discoveries relative to scripted rotation of approximately **−0.470 GRU** and **−0.736 exploration MLP** per 32 decisions, with no real Forge model changes.

## New actual temporal gradient

`scripts/benchmark_gru_truncated_bptt.py` trains a GRU with the same 22 causal inputs, 12 recurrent units, 4 candidate outputs and 32 synthetic decision steps per episode. Training updates are made in blocks of **8 consecutive decisions**, with exact reverse-mode gradients through the GRU hidden state **within each block**. The recurrent state persists numerically between blocks, but its gradient is detached there. The same chosen-source squared-error learning target is used: the direct synthetic discovery outcome after the selected source inspection. No unseen source reward or privileged future resource state is provided.

Finite-difference tests check the analytical derivative of the summed four-step sequence loss for each reset, update, candidate and output parameter group. They also verify that later losses contribute to earlier recurrent-gate gradients, a substantive difference from the existing one-step implementation.

## Controlled comparison

Train two GRUs from the same initial weight seed and equivalent synthetic pretraining budget (180 episodes per training seed), one with existing single-step truncated gradients and the other with eight-step truncated BPTT. Compare them alongside scripted least-recently-sampled attention on the **same pre-generated immutable latent timelines**. The held-out test has three independent training seeds (11,17,23), four resource-volatility regimes, three hidden update rates and thirty episodes per seed/regime/rate cell. An episode has 32 one-source inspections. Report mean direct discoveries, least-visited source count, signed trajectory digests and per-cell neural-minus-scripted differences.

The training update frequency and gradient scale are not identical between methods (one-step updates each decision; BPTT updates each eight decisions); this is an exploratory algorithm comparison with the same observation/episode budget, not a perfectly isolated comparison of sequence length alone. A future experiment should independently control optimizer update counts and per-step effective learning rates before making architectural superiority claims.

## Safety boundary

All worlds and outcomes are synthetic. The first successful real Forge four-source controlled benchmark remains scripted **8/16** versus frozen neural **5/16** witnessed changes, each at ten inspections. No new weights have been loaded into Forge and there is no new Minecraft action authority, LLM, pathfinding, hauling, crafting, or online learning. Synthetic training gains cannot authorize deployment. A later candidate would need independent seed/regime robustness, Python/Java parity and new held-out real Forge canaries.
