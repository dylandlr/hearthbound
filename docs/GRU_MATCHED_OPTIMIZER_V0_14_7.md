# Hearthbound v0.14.7 — Matched-optimizer GRU sequence training

## Verified prior result

PR #167, eight-step truncated BPTT, passed all six GitHub checks. The archived three-seed study found that the original **one-step GRU** averaged **−0.47037** directly observed discoveries versus scripted across 36 frozen-timeline settings, whereas the **eight-step BPTT GRU** averaged **−1.43889** discoveries versus scripted. Every training seed had a negative BPTT mean. By regime, one-step versus BPTT differences were: in-distribution −1.530 vs −2.659; low volatility −2.059 vs −3.385; unequal volatility +1.915 vs +0.837; high volatility −0.207 vs −0.548.

The earlier comparison did not control optimizer-update cadence. The one-step GRU updated after every decision, while the BPTT model updated after eight. The result cannot establish that temporal backpropagation alone caused worse learning.

## New comparison

`scripts/benchmark_gru_matched_optimizer.py` controls the optimizer schedule directly.

- Train two GRUs with the same 22→12→4 architecture, initial numerical seed, episode count and underlying pre-generated resource changes.
- Both receive exactly 32 selected-source training outcomes per episode, with 8 outcomes accumulated per optimizer update, and **four optimizer updates per episode**.
- Both use the same learning rate of 0.016 per eight-step batch, 3.0 global gradient clipping threshold and division by eight after gradient aggregation.
- **Buffered one-step:** differentiate each selected-source squared-error loss through only its current GRU cell; aggregate eight gradients before updating.
- **Eight-step BPTT:** differentiate the sum of the same eight selected-source losses backward through all eight recurrent states, with the hidden gradient detached between blocks.
- Only a selected source's actual observed synthetic outcome is used for learning. Hidden resource states and rewards of unselected sources remain unavailable.
- Different training policies can choose different sources after their weights diverge. Matching the optimizer schedule does not guarantee identical later action histories; the held-out **evaluation** gives all policies identical latent trajectories.

The tests verify equality of buffered gradients to the sum of eight independent one-step gradients, evidence that BPTT gradients differ on recurrent parameters, exact optimizer update counts, replay determinism, and policy-observation privacy.

Evaluate three training seeds × four held-out source regimes × three update rates × 30 episodes with 32 inspections per episode. Report mean directly observed discoveries and minimum source-visit diversity relative to scripted rotation, using signed shared latent-trajectory manifests. **No Forge model weights are changed or deployed.**

This is a control for optimizer update **count and nominal learning rate**, not a comprehensive isolation of temporal credit. Effective gradients and selected training trajectories still differ. Follow-up work should use common behavior-policy training data, explicitly measure prediction calibration, and test genuine delayed-dependency tasks before making broad claims about recurrent memory. Passing simulator thresholds never authorizes model promotion or Minecraft task powers. No LLMs.

## Matched-control results (GitHub Actions 41976348325)

The initial benchmark CI passed and archived the actual three-seed, 36-cell comparison. Buffered one-step GRU averaged **−1.51852** directly witnessed discoveries versus scripted; eight-step BPTT averaged **−1.43889** per 32-decision episode. The resulting BPTT minus buffered one-step difference was **+0.07963**, a small descriptive improvement.

Per-regime BPTT minus buffered result: in-distribution **−0.14815**, low volatility **+0.25555**, unequal volatility **+0.11852**, and high volatility **+0.09259**. Per-training-seed differences were approximately **+0.08611** (11), **−0.38333** (17), and **+0.53611** (23). BPTT is **not consistently superior across training seeds** and both equal-update neural arms are substantially worse than scripted overall.

This changes interpretation of the previous v0.14.6 result: matching the optimizer-update cadence largely removes BPTT's earlier apparent disadvantage relative to one-step gradients, but does **not** establish a valuable recurrent attention policy or justify deploying weights in Minecraft.

The independent signed `report_gru_matched_admission.py` now explicitly checks that BPTT beats buffered one-step on every seed **and** is not worse than scripted on every seed; the current candidate fails. CI always sets `minecraft_model_promotion_authorized=false`.
