# Hearthbound v1.6 — Server clock integration

Implemented: Java 17 ServerTickClock, ForgeServerTickObserver and 11 clock tests. The repaired ServerTickEventLedger has 13 standalone tests.

Forge callback listens to server END ticks and samples getServer().getTickCount(). The adapter is in-memory only and has NOT been ForgeGradle compiled or run in Minecraft. The logical clock constructor supports a recovered offset, but the observer currently initializes at 0: no SavedData persistence exists yet.

Caveats:
- The same tick can contain many events; ServerTickEventLedger ordinal controls ordering.
- The first sample establishes a clock baseline rather than guessing historical tick count.
- World time is not the canonical monotonic clock.
- A tick callback is not evidence of Create input consumption or output generation.
- Restore SavedData before registration and avoid per-dimension tick callbacks.
- For reproducible training, also persist event source ordering and randomness.

Next: SavedData persistence with durable flush boundaries, Forge compilation and an authoritative Create millstone inventory mutation hook. Do not claim deterministic restart replay until those are tested.
