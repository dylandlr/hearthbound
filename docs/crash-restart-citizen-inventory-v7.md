# Crash restart v7 — actual villager resource invariant

The manually dispatched isolated process-halt workflow now requires the post-crash Minecraft JVM to load the original villager, match its Hearthbound citizen UUID, and inspect its actual persistent entity NBT. For the deliberately **pre-mutation** hook, the villager must retain its initial two wheat, and it must not have a delivery receipt for the interrupted operation. The Create millstone must likewise remain empty. The second-JVM log must emit both `HEARTHBOUND_CRASH_RESTART_CITIZEN_PASS` and `HEARTHBOUND_CRASH_RESTART_MACHINE_PASS` for the exact UUID.

This intentionally makes missing or unsaved entity state an experiment failure rather than interpreting journal persistence as victory. A pre-crash clean GameTest baseline may not have the same citizen as a later re-run, and an abrupt halt does not save newly spawned entities. **The first manually dispatched run is expected to determine whether the existing fixture is suitable**, not to prove crash safety by construction.

The read-only verifier still halts after inspection. No claim is made about after-mutation crashes, repeated deliveries, automatic transaction retirement, or exactly-once settlement.
