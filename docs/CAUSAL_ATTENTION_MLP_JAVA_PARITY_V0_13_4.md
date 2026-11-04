# Hearthbound v0.13.4 — Frozen causal MLP Python/Java parity

The corrected four-arm Forge experiment in PR #154 produced verified **6/6 direct matching observations** in each seeded arm with a common resource schedule and scripted citizen attention. The policy names do not imply trained neural attention executed. Before allowing a learned model to select inspections, verify the actual simulator-trained neural scores in a Java execution environment without exposing Minecraft commands.

## Evidence and model

`scripts/export_causal_attention_java_parity.py` trains the fixed 16→16→4 neural attention network using the **causal-history simulator** (seed 11, 500 episodes), not Minecraft-trained weights. Only history-derived features are supplied: never inspected, last observed availability, normalized age and empirical observed change frequency. The export stores complete weight tensors, dimensions, training provenance, and a canonical model-tensor digest. A deterministic suite of 51 vectors includes mixed known/unknown histories and zero-padded candidate slots.

`src/test/java/dev/hearthbound/evidence/CausalAttentionMlpParity.java` independently reads and validates the frozen format, performs Java ReLU inference, and compares every score to Python with absolute tolerance 1e-9. It requires all inference values finite, masks nonexistent candidate slots when selecting a source, and rejects incorrect dimensions/schema/fixtures. It has no dependency on Forge or Minecraft and cannot authorize an action.

## Acceptance

The real dedicated-server workflow performs the Python export and Java parity check **before starting Minecraft**; a parity failure blocks acceptance for every policy arm. Each trial archives the frozen weights and Python score fixtures. This is *inference parity*, not a claim that the transferred feature scale is calibrated, the policy improves resource discovery, or the neural model was permitted to choose an inspection.

## Next milestone

Once parity is green, implement an explicit disabled-by-default, server-side policy adapter that constructs exactly these history-derived features, logs the neural recommendation and scripted action together, and allows the learned choice only under a separate opt-in experiment flag, one-inspection-per-five-ticks gate, and full provenance. No LLMs.
