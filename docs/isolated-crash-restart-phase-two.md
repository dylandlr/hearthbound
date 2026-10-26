# Isolated Minecraft crash probe: phase two

This extends the manually dispatched disposable-world crash workflow with a second JVM. The first server halts after forcing a write-ahead delivery attempt and before the actual Create inventory mutation. CI must find the corresponding saved world's **existing** `level.dat`; it explicitly fails if the crash happened before the world became restartable. It then boots `runServer` on that same world path under the opt-in `HEARTHBOUND_CITIZEN_RECOVERY_STAGE=inspect_after_crash` mode.

The read-only restart check requires both the citizen work-order and delivery-attempt journals to exist and records `HEARTHBOUND_CRASH_RESTART_JOURNALS_PASS`. It exits without authorizing a replay. The workflow also rejects any unexpected successful supply log marker and collects logs from both Minecraft JVMs.

**Limits:** This is not a complete crash-recovery acceptance test. The restarted server does not yet verify the actual villager's NBT wheat balance or the Create millstone inventory, and it stops early rather than running the normal controller for an extended interval. The present checks cannot establish whether unflushed entity or block-entity changes survived. A baseline saved world and an operation-specific restart verifier will be needed to make that a meaningful no-replay claim. In particular, a passing journal check must not be interpreted as proof of exactly-once inventory delivery.

The workflow is manual-only and requires two human opt-ins for the destructive disposable-world test. The ordinary acceptance workflow never enables the crash hook.
