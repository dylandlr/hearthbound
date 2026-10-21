# Hearthbound v3.5 — Live pre-decision observations

The autonomous mill researcher now calls `LocalMillExperimentSensor.observe` once at a real eligible research decision boundary. The identical immutable observation source feeds both `ResearchDecisionComparison` and the executed PERSONALITY policy. After `SableHauling.assign` accepts the physical job, `ResearchTrainingRuntime.afterAssigned` saves the 11-feature schema-v1 vector keyed by that job UUID to `ResearchObservationSnapshotsSavedData`.

## Guarantees
- No substituted successor observation or synthetic sample.
- Save-cycle persistence with Minecraft world SavedData.
- Job/citizen identity and tick stored with defensive feature copies.
- No global Minecraft world visibility is added to the policy.
- Snapshot duplication with changed data fails; schema and feature range validated.
- Separate observation store does not issue research credit.

## Remaining limitations
- Minecraft SavedData, across snapshots, bindings, rewards and replay, is NOT an atomic transaction. Partial saves and crashes may leave an incomplete research sample; reject rather than infer.
- The snapshot store retains up to 10,000 snapshots, then rejects additions; expiry/pruning requires coordinated retention policy.
- Fatigue and scarcity readings currently come from existing stubbed values, not real physiological sensors.
- This is only s_t: successor s_(t+1), done/terminal semantics and a single durable joined transition store remain future work.
- Unit tests are authored, but Forge CI, live gameplay and restart verification are outstanding.

## Next acceptance
Forge compilation, unit tests, Minecraft simulator fixture proving same observation for executed policy and saved vector, crash/restart consistency, and a true successor observation captured after verified outcome.
