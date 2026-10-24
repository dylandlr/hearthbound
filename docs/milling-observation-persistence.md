# Milling observation checkpoints

The live processing audit stores full before/after ItemStack NBT, tick, dimension, position, session and observation UUIDs, recipe IDs and evidence quality in overworld SavedData. Records are copied on ingress and read. Matching duplicate IDs are ignored; conflicting IDs and malformed persisted records are rejected. Capacity is 10,000 records; overflow is logged without interrupting processing.

The motor GameTest checks that the actual event was recorded, verifies NBT serialization/reload equality and checks duplicate/conflict behavior. After verifying that disconnecting the motor stops milling, it flushes the overworld SavedData and writes a separate expected NBT snapshot.

The dedicated-server smoke workflow then locates the saved GameTest world and boots it in a second JVM. An opt-in check, enabled only by HEARTHBOUND_RESTART_EXPECTED, compares the entire loaded journal with the expected snapshot, requires exactly one observation, and checks duplicate/conflict rejection without altering the record. CI requires the HEARTHBOUND_RESTART_PASS marker. The expected snapshot is only a comparison fixture; the journal loads through the normal overworld SavedData path. Both NBT files are retained with the workflow diagnostics.

This verifies a saved checkpoint across a process restart. It does not simulate a crash during processing. Machine state and journal files are NOT one atomic transaction. A newly generated observation UUID does NOT deduplicate a replayed physical operation. Research credit remains disabled pending persisted pre-operation identity and crash reconciliation. The diagnostic journal does not automatically expose hidden recipe knowledge to agents.
