# Hearthbound v2.7 — Bounded research decision traces

This milestone supplies a pure, synchronized Java diagnostic journal around the existing same-observation SCRIPTED vs PERSONALITY comparison.

## Schema

`schemaVersion: 1`; `citizens[]` has `citizenId` and `decisions[]`. A decision includes `gameTick`, `scripted` and `personality` policy decisions (`action`, nullable `recipeId`, finite `utility`), a `disagreement` flag and a rule-based `explanation`.

## Guarantees

- Bound trace retention by citizen; old entries are evicted.
- Reject duplicate/out-of-order per-citizen ticks, including after eviction.
- Snapshots are detached and immutable, and JSON export is deterministic by citizen ID.
- Reject non-finite utilities and malformed IDs.
- This journal stores **decision diagnostics**, not proof of experiments or causal reward.

## Limitations / next gate

The journal is in-memory and not wired to Minecraft's citizen cadence, disk persistence, command/RCON exports, or dashboard yet. It has JUnit tests but requires Forge CI validation before being treated as deployed. Next integrate journal once per actual citizen decision tick, add server-side controlled JSON export and dashboard plots, and measure per-policy outcomes from verified events rather than inferred counterfactuals.
