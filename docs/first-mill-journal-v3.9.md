# First Mill v3.9 — persisted candidate evidence

## Implemented
`MillEvidenceJournal` is a per-dimension Minecraft SavedData store of unique milling experiment candidates keyed by hauling job UUID. It records citizen UUID, millstone position, observed processing tick, output tick and flour counts.

`MillExperimentTrace.sampleCycle` records an entry when the prior delivery and sampled Create millstone observations reach the output-observed phase. `/sable mill-evidence <job-uuid>` reads back the record, clearly labeled CANDIDATE and NO_RESEARCH_CREDIT. Repeated insertion with the same job UUID and exact payload is a no-op; differing payloads with the same UUID are rejected. Invalid tick ordering is rejected.

## Scientific and durability limitations
This is a **world-save-persistent candidate evidence record**, not an atomic transaction with Create's processing code. Minecraft `SavedData` durability requires successful world save; unexpected JVM termination before saving can lose the candidate. The physical world and journal may be saved at different instants. The record is based on sampled machine states and could be confounded by concurrent access. No recipe is unlocked or agent rewarded; there is no machine-completion callback.

## Tests
`scripts/rcon_sable_first_mill.py` now verifies an entry exists for Sable's real physical milling job and that the journal explicitly withholds research credit. CI must pass on the updated revision before this is claimed validated. Additional startup/restart tests and exclusive machine use are required before using candidates for learning.
