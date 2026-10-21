# Hearthbound v3.1 — Persistent verified-reward replay

The Minecraft `SavedData` journal `hearthbound_verified_reward_replay_v1` now retains completed, causally attributed research reward records after world saves. It is invoked after the verified reward callback has journaled the corresponding Create processing award.

## Stored schema v1
Job UUID, citizen UUID, decision tick, outcome tick, action `PROPOSE`, recipe ID, trusted evidence ID and a distinct personal / colony / research reward vector. Serialization includes a schema version.

## Guardrails
- Same-job replay is idempotent only when record contents match; conflicting records are rejected.
- Distinct jobs cannot share an evidence ID while both are retained.
- Invalid action, missing recipe/evidence, reversed ticks and malformed schema are rejected.
- Fixed upper bound of 10,000 records per level, with oldest-first eviction.
- The journal is diagnostic: it cannot invent rewards or drive the policy.

## Operational caveats
- This is **completed reward replay**, not a full reinforcement-learning transition. It does not include state vectors, next observation, terminal status, policy probabilities or learning updates.
- Pending job-to-decision bindings are still in memory. A restart before receipt completion leaves a legitimate award unpaired; the integration intentionally fails closed rather than fabricating attribution.
- SavedData durability depends on Minecraft successfully saving world data. Award persistence and replay persistence are not a transaction; a crash between them may leave a rewarded job without replay data.
- A 10,000-record FIFO cap also means historical evidence replay protection requires a separate persistent evidence index if stronger forever-once semantics are needed.
- Neither a Forge compile nor a real Minecraft restart test has been verified in this change.

## Next acceptance gate
Run JUnit, Forge CI and dedicated-server smoke. Save/restart and compare replay UUIDs against `MillResearchRewards`. Validate that tainted jobs yield no entries. Then make pending bindings durable and capture successor observations before implementing an offline MLP.
