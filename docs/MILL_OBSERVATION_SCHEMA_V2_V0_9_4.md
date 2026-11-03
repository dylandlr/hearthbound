# v0.9.4 — Frozen MLP with versioned ten-feature observation contract

The previous v0.9.3 source-aware scripted reference planner passed the complete real Forge/Create Minecraft experiment (both SCRIPTED and TRAINED_MLP server jobs, plus comparative artifact). The reference planner remains a non-learning control.

## New observation schema

`hearthbound.mill-observation.v2` is a **ten-feature ordered tensor**:

| Index | Feature | Encoding |
|---|---|---|
| 0 | powered | 0 or 1 |
| 1 | mill_wheat_present | 0 or 1 |
| 2 | mill_flour_present | 0 or 1 |
| 3 | mill_blocked | 0 or 1 |
| 4 | verified_experience_norm | min(10, count)/10 |
| 5 | source_unknown | one-hot |
| 6 | source_empty | one-hot |
| 7 | source_available | one-hot |
| 8 | task_active | 0 or 1 |
| 9 | source_stale | 0 or 1 |

Exactly one of indices 5–7 is set. `UNKNOWN` is never converted to empty. A known source observation older than 100 Minecraft ticks is treated as UNKNOWN, and `source_stale=1` records why. The schema rejects negative experience and impossible or future timestamps. All feature values are finite in [0,1].

## Grounding in actual Minecraft

The existing read-only source-aware probe now includes `observation_schema=hearthbound.mill-observation.v2` and `tensor_v2=...` along with its decision. The dedicated Forge tests assert the exact unknown/empty/available one-hot flags, an idle powered mill and non-stale observation. The reporter independently verifies ten-feature vectors, their schema and the three grounded states, then archives `observation-v2.json` in both policy arms.

## What is deliberately not changing

The original 5→12→4 MLP's model bytes and SHA-256 are unchanged. We do not feed a ten-feature tensor to a five-feature model, silently pad, or represent the new scripted reference planner as trained intelligence. This is an observation candidate to support a later **new** trained model with its own model ID, train/validation split, held-out scenarios and runtime parity tests. There is no online learning or autonomous resource-seeking behavior.

## Next training milestone

1. Acquire diverse real Minecraft scenarios (especially shortages, unknown inventories, delays and blocked machinery), logging actual state transitions and not just terminal successes.
2. Build a fast, reproducible partially observable trainer for ten-feature observations, with separate personal and colony reward contracts and strong scripted controls.
3. Train a new model artifact while preserving v1, then evaluate on held-out worlds and compare observed, not fabricated, Minecraft outcomes.
