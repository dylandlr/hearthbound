# Hearthbound v1.7 — Overworld-persisted clock
The Forge END-tick observer now increments an overworld-scoped SavedData value. See `HearthboundClockSavedData` and `PersistentTickCounter`.

**Local:** Nine pure Java counter tests passed under Java 17. **Unverified:** ForgeGradle compilation, world-save/load GameTest, runtime tick callback.

Persisted SavedData is checkpoint persistence, not a per-event fsynced journal. After an unclean shutdown, the logical tick may roll back to the last world-save checkpoint. Do not rely on SavedData tick as a globally unique event ID. Operation UUID and a durable append-only event journal must remain authoritative for reward deduplication.

The event is sampled at server END phase: events during a tick must additionally record phase and deterministic event ordinal. Shared storage is taken from the overworld for all dimensions. Additional tests required: world save/restart, Nether transactions, hard-crash recovery against event journal, integrated Create processing and Forge compilation.

See versioned local source package hearthbound-saveddata-clock-v1.7.zip.