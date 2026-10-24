# Milling observation checkpoints

The live processing audit now stores full before/after ItemStack NBT, tick, dimension, position, session and observation UUIDs, recipe IDs and evidence quality in overworld SavedData. Records are copied on ingress and read. Matching duplicate IDs are ignored; conflicting IDs and malformed persisted records are rejected. Capacity is 10,000 records; overflow is logged without interrupting processing.

The motor GameTest checks the actual event was recorded, verifies NBT serialization/reload equality and checks duplicate/conflict behavior. This is an in-memory NBT round trip, not a process-restart test.

SavedData flushes on world saves. Machine state and journal files are NOT one atomic transaction. A newly generated observation UUID does NOT deduplicate a replayed physical operation. Research credit remains disabled pending persisted pre-operation identity, disk restart testing and crash reconciliation. The diagnostic journal does not automatically expose hidden recipe knowledge to agents.
