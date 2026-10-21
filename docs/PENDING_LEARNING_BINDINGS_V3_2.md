# Hearthbound v3.2 — Restart-safe pending research attribution

## Implemented
- New `PendingLearningBindingsSavedData` contains a version-1 policy decision, citizen UUID, game tick and physical hauling job UUID.
- `ResearchTrainingRuntime.afterAssigned` persists the binding after successful physical job admission.
- `afterVerifiedAward` loads the persisted binding, validates the award through `VerifiedTrainingTransitions`, adds it to `VerifiedRewardReplaySavedData`, then removes the pending record.
- Repeated callbacks for a job already in persistent replay return without re-crediting.

## Safety contracts
- Pending bindings confer no reward.
- Missing binding never fabricates attribution.
- Conflicting UUID binding is rejected; equivalent reinsertions are idempotent.
- 10,000 maximum pending jobs per level; when full, fail closed instead of silently discarding active provenance.
- Pure round-trip, duplicate and malformed-binding tests included.

## Important boundaries
- Minecraft SavedData is save-cycle durable, **not a synchronous write-ahead log**. A crash before dirty data has been written can lose a pending binding.
- SavedData writes across job, award, binding and replay journals are not atomic. A crash at the boundary still requires recovery/reconciliation to prevent lost training samples, not to grant rewards.
- In-memory diagnostic traces are not restored, but their authorized proposal's minimal decision metadata is preserved with the pending binding.
- No `s_{t+1}`, done flag, fully encoded observation, offline trainer or loaded Minecraft acceptance report yet.
- Propose remains gated by real physical work ownership and existing world-event verification.

## Required test matrix
1. JUnit SavedData round-trip.
2. Forge compile and dedicated server scenario.
3. Save, stop, restart after haul admission; finish machine processing; verify one reward and one training record with matching job/evidence.
4. Restart after award but before replay save; compare journals and flag missing replay attribution.
5. Run tainted/quarantined/cancelled experiments: zero completed training entries.
6. Verify 10,000-entry cap and identical UUID replay.
