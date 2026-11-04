# Hearthbound v0.13.5 — Opt-in neural attention selector inside real Forge

The baseline citizen attention scheduler remains **LEAST_RECENTLY_SAMPLED**, at most one source inspection per citizen every five Minecraft ticks. This milestone adds the first *explicitly operator-enabled* alternative: `NEURAL_CAUSAL_MLP_OPT_IN`, using the frozen simulator-trained causal-history MLP from PR #155. It authorizes **only which pre-registered source is inspected**; it cannot move, haul, craft, register watches, inspect counterfactual inventories or issue Minecraft task commands.

## Operator-controlled enablement

Commands require permission level 2:

```text
/hearthbound citizen_neural_status
/hearthbound citizen_neural_enable
/hearthbound citizen_neural_disable
```

The model is not automatically active even when its weight file exists. Enablement loads a fixed file named `hearthbound-causal-attention-mlp.txt` from the world-save root, rejects symlinks and invalid model shapes, and reports the frozen model-file SHA-256. Disablement reverts immediately to the scripted baseline. Level registry state is not persisted; after a dedicated-server restart neural selection is disabled again. A failure during model inference also fails closed to the scripted choice.

## Observation contract

For each citizen the model receives, in deterministic coordinate order, up to four already registered watches. Each source contributes exactly four bounded features: never directly inspected, last directly observed available, normalized age since last successful direct inspection, and empirical frequency of differences between directly observed states. Unknown sources use only unknown defaults; no current chest state, hidden volatility, global registry state or other citizen's knowledge is used. Missing candidate slots are zero-padded but **never selectable**.

One selected source per citizen per sampling interval is preserved by the existing spent-citizen gate. All source selection happens before any source inventory inspection. Every actual choice is recorded with `policy=NEURAL_CAUSAL_MLP_OPT_IN` rather than mislabeling it as scripted; existing paired-outcome, hash-chain, run-finalization and citizen-experience validators now retain actual policy provenance. The outcome is still the selected source only. Training does not occur in Minecraft.

## Real-server acceptance and evidence

The existing four-arm Minecraft CI retains its original scripted baseline and seeded experiments. The `TRAINED_MLP`-labeled seeded arm, **only after the original restarted-server validation is complete**, enters a separate opt-in neural canary. It stages the frozen model in the save directory, requires an initially disabled selector, explicitly enables it, registers two real source watches, and requires a matched neural-policy-tagged source-selection/outcome receipt. The canary records a fresh finalized run and exports a separate causal experience dataset, then turns the neural selector off. This isolates the new execution from the original controlled resource-intervention coverage report.

Production `CausalAttentionModel` forward-pass scores are compared against all 51 Python inference fixtures independently of the pre-existing pure-Java parity verifier. This ensures the exact production model loaded by Forge has the expected inference behavior.

## Scientific limits

The model is trained **only in a synthetic simulator**, and feature calibration to Minecraft ticks is experimental. A successful canary would prove one neural-chosen inspection occurred on a real Forge server, not that neural attention outperformed the baseline. Valid comparative learning outcomes require equally timed intervention schedules, multiple independent world/fixture runs, pre-registered evaluation measures, and quantified uncertainty. The neural model can inspect but cannot initiate mining, crafting, hauling, movement or social tasks.

No LLMs are involved.
