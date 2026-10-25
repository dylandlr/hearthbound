# Operation-bounded milling observations v1

The real Create integration journal previously supported looking up an observation by machine position alone in the fixture. That makes consecutive operations on the same millstone ambiguous. `MillingObservationSavedData.uniqueInWindow(dimension, position, minTick, maxTick)` now requires a bounded server tick window and rejects both missing and multiple matching observations. It returns a defensive copy.

A Forge GameTest verifies the selector against the actual wheat-milling observation. It also inserts a **synthetic second observation into an isolated reloaded journal instance** to verify that distinct tick windows select the intended record and that overlapping windows fail closed. This simulated second record is not a second Minecraft milling operation and cannot earn research credit. The real journal and its restart evidence remain unchanged.

Next: the server-owned durable operation intent must persist an authoritative start tick and completion bound, and the credit fixture must look up by that window rather than position alone. Then the GameTest can safely perform two *real* Create mutations on one machine, preserving per-citizen operation and credit identities.
