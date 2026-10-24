# Hearthbound v1.5 — Deterministic event timing

Implemented: `ServerTickEventLedger` (pure Java 17) and 13 standalone tests.
Local execution: `javac --release 17` then `java ...ServerTickEventLedgerTest`.

Every operation event carries (tick, per-tick ordinal, operation UUID, kind, world, dimension, machine position, recipe). The prototype rejects regressing ticks, duplicate UUID/kind pairs and unordered recovery.

**Not implemented:** actual server tick capture, persistence, Create callback, state snapshots, replayable world simulation, RNG capture or agent observation filtering.

The authoritative production clock should be a monotonic, persisted Hearthbound server tick/sequence counter. `ServerLevel.getGameTime()` is useful context but should not be treated as a globally unique clock across worlds or as a guarantee of reproducibility. Invoke on the logical server thread; record source dimension/time independently.

To make this truly deterministic, persist every accepted event before acknowledgment; restore event order and counters; record random draws or seed and invocation order; pin Create/Minecraft/mod versions and schedule agent decisions deterministically.

Do not expose server recipe IDs or hidden machine state to citizens if their observations are supposed to be partially observable.

Next: Forge server tick adapter, durability integration, input/output mutation observer and multi-seed Minecraft GameTests. No live Forge compilation claimed.
