# Hearthbound v0.9.7 — Real Minecraft neural-Q shadow evaluation (read-only)

This milestone compares a **simulator-trained** neural Q model's predictions to the source-aware reference decisions using evidence actually observed in two Forge/Create dedicated servers. It does not train on, interact with, or control those Minecraft environments.

## Evidence dependency

The existing `compare-policy-arms` GitHub Actions job can start only after both Minecraft server tests succeed, including actual Create flour processing, verified Sable task experience and post-restart persistence.

That comparison job now regenerates the deterministic v0.9.5 simulator neural model from fixed seed 11, 300 synthetic episodes, using the same SHA-256-checked checkpoint and 48 Python-to-Java parity fixtures. It compiles standalone Java 17 with no Forge dependency, then reads each arm's archived `smoke-rcon.log`.

The Java shadow checks all three source states `EMPTY`, `UNKNOWN` and `AVAILABLE` from authentic `REAL_OBSERVATION_V2` records, along with the independently recorded `REAL_SOURCE_PLAN` scripted baseline. It checks ten-feature source masks, powered idle mill preconditions, ordered action labels, and exact model feature order. It computes three neural Q-values and an argmax prediction for each state but **does not call or access any Minecraft controller**.

A strict reporter requires exactly three observations in each of two policy arms, identical fixed model checkpoint checksums, valid Q-value argmax, matching live fixture Q-scores and explicit `read_only=true dispatch=false` provenance. The resulting `real-neural-q-shadow.json` reports agreement counts and disagreements without inventing gameplay improvement.

## Interpretation

- World observations come from real Minecraft.
- Neural weights and learning originated exclusively in the abstract simulator.
- The comparison is *offline inference on Minecraft observations*, not neural execution in Minecraft, and does not establish reward improvement, gameplay safety, or useful transfer.
- Both policy arms have the same three controlled source states; the six observations are **not six statistically independent Minecraft evaluations**.
- No action authorization, model promotion, or online RL is performed.

## Next scientific gate

Expand to independent Minecraft seeds and task scenarios; log interrupted processes, stale/missing inventory data, occupancy, and duration. Then evaluate both failure and success evidence against a learned policy, with locked reward definitions and genuine held-out trials. Only after read-only testing justifies it should a separately restricted one-shot neural task proposal be considered.
