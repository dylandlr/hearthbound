# Hearthbound v0.11.3 — Citizen-owned source knowledge (experimental)

Stacked on #133, which itself stacks on #132. This PR is a **candidate implementation**, not a claim of CI success until the dedicated server jobs complete.

## Data contract

- Storage: marked Sable villager's Forge persistent NBT under `ForgeData."hearthbound.source_knowledge.v1"`, not global source truth.
- Each remembered source key is dimension + block coordinates. Each record contains state, wheat count, observation game tick, personal revision and `DIRECT_FORGE_OBSERVATION` provenance.
- Write trigger: only after a valid, known `SourceWheatObservation.inspect` result from a loaded chunk and the marked nearby citizen. A repeated unchanged observation refreshes the last-seen tick.
- Memory bound: max 16 entries/citizen. FIFO by last observation, replacing a previously seen key.
- Freshness: `FRESH` when `0 <= current_game_tick - observed_tick <= 40`; otherwise `STALE`. Absence is `UNKNOWN`. A reset world clock is conservatively stale.
- Operator-only `/hearthbound knowledge_source <x> <y> <z>` inspects precisely one marked Sable within 16 blocks, returning one RCON line. It never opens a container, force-loads a chunk, executes a task or exposes the cache to another citizen.
- Source coordinates and dimension are part of the key; no cross-dimension conflation.
- No social communication, belief synthesis, CNN, LLM, learned memory policy, or task authorization in this slice.

## Real-server acceptance

The existing SCRIPTED and TRAINED_MLP dedicated-server trial arms still require empty → four wheat → empty perception receipts. Each now also queries the saved citizen memory (expect EMPTY, 0, direct evidence, `action_authorized=false`). The existing stop/save/restart test checks the same memory state both before shutdown and after actual Forge restart.

## Known limitations / next tests

- A remembered source may be outdated even if technically `FRESH`, because other actors can change it between observations. Any real execution must independently validate the live source and resource permissions.
- `knowledge_source` is admin-only and restricted to a nearby marked Sable; it is not a citizen-to-citizen communication primitive.
- The cache persists with Sable's entity save; it does not create a permanent omniscient global map. If the villager is permanently removed, its private memory disappears.
- The initial acceptance checks persistence of the final source state, not full staleness transitions, source eviction or agent isolation. Add dedicated tests for these before exposing memory to a trained planner.
- Perception receipts are monitor-local and remain independent of personal memory revisions.

## Follow-on v0.11.4

Add multi-citizen identity/isolation tests and an explicit communication transaction with sender, recipient, evidence provenance, delay, trust and expiry, without sharing memory globally. Train or compare policies only after these safety/observability contracts are accepted.
