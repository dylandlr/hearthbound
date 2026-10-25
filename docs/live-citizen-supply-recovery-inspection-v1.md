# Live citizen milling recovery inspection v1

`CitizenSupplyInspection.inspect` evaluates the real Minecraft server's citizen, villager persistent data, Create millstone and pre-operation journals without mutating any of them.

A successful delivery now writes a matching `HearthboundLastSupplyOperation` UUID and `HearthboundLastSupplyBefore` wheat count to the villager's persistent NBT. Inspection resolves the prepared operation ID from the durable work-order journal; checks for a write-ahead attempt; validates the villager's receipt and millstone position; checks the active citizen registry's IDLE task and compares the post-transfer wheat counter to the pre-transfer count. Only then can it classify a delivery as `COMPLETED_OBSERVED`. If the work order is corrupt, missing or inconsistent, it returns `AMBIGUOUS_BLOCKED`.

The live Minecraft GameTest now requires a `COMPLETED_OBSERVED` classification for its actual citizen walk-and-deliver transaction. It cannot use the pure synthetic recovery contract alone.

**Limits:** This is a read-only runtime assessment, not a disk-restart test or durable completion commit; the villager's receipt and registry state are persisted independently from Create. Work-order reconciliation, operation retirement, crash-injection tests and restart evidence remain future milestones.
