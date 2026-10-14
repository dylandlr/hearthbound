# Haul cancellation acceptance

`/sable haul-cancel` cancels a job only while Sable has no cargo stored in her job NBT. It releases the source claim on successful cancellation.

Acceptance scenarios: (1) assign and immediately cancel before pickup; reassignment of source succeeds; (2) cancel after pickup returns an error and retains the cargo; (3) cancel an already complete job returns an error; (4) two Sables claiming the same source remain serialized; (5) compile actual Forge sources; (6) perform a real server playtest.

This is **not** a persistence or crash-safety solution. Claims remain in memory, and villager death/unload/restart recovery still needs authoritative reconciliation. Do not cancel cargo-bearing jobs by deleting NBT.
