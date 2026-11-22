# Hearthbound persistent citizen decision history v0.5

Research basis: MARBLE / MultiAgentBench (ACL 2025) and PA4 reading dossier P42, P06, P11 and P32/P33. Extends the live four-citizen job/decision joins from #206 with multi-job *research observation history*.

## Implemented
- `CitizenDecisionHistory` is a pure Java 17 bounded, explicit-state log with two states: `ASSIGNED` and `PHYSICALLY_COMPLETED`. Keys include real citizen, job, task, episode, source/target positions, observation/decision IDs, revision, and four chronology ticks.
- Registration occurs immediately after existing successful physical assignment and citizen memory save; completion is recorded only when the existing physical `SableHauling.completedJob` and `completedAssignment` checks succeed. Observation journal errors do not retry/cancel/alter physical work.
- Existing `ColonyData` SavedData persists all entries and an explicit capacity denial counter across ordinary world saves/restarts, with duplicate/contradictory state rejected on load. Max 1,024 entries per dimension; no silent FIFO eviction or old ID reuse. This cap intentionally limits long sessions.
- Operator-only read-only `hearthbound-colony history-audit` shows assigned/unverified and physically completed counts. This records **incomplete work as incomplete**, rather than converting it to an invented success.
- The existing live four-citizen RCON acceptance now demands four stored, physically completed records and zero denied-capacity entries.

## Limitations
This is *not* an fsynced/append-only crash-safe journal, atomic inventory transaction, saved-unloaded-citizen auditor, or any kind of neural policy training. Vanilla SavedData is not guaranteed to commit atomically with villager NBT and chest inventory. After a crash or between write/save boundaries, an assignment or terminal receipt may be absent; never reconstruct or award credit from the mere absence of a history record. The current-session episode restriction means a task completed only after a restart will not be incorrectly stamped as same-session verified history, even if the physical recovery system later resolves it.

Only the scripted `DETERMINISTIC_TRAIT_RANK_V1` decision baseline is observed. The log contains no peer communications, multiple-role work histories, political beliefs or actual emergent organizations. Its production baseline remains the existing four deliveries in one disposable world; world-level replication and MARBLE cooperation scores are not yet established.

## Test gates
`python3 scripts/test-civilization-contracts.py` runs the new `CitizenDecisionHistoryTest` alongside existing pure Java suites. The actual `.github/workflows/real-four-citizen-colony.yml` must compile Forge and pass live physical acceptance with the extra `history-audit` assertion before any live claim.

Future work should add *world-bound evidence journal reconciliation*, an event exporter that distinguishes multiple jobs over time and failure types, and matched-seed topology comparisons. Do not equate persisted memory with physically verified performance or count four workers as four independent world replicates.
