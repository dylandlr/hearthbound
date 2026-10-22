# Hearthbound v3.5 — Correlated millstone diagnostics

The previously implemented Create `process()` Mixin and JAR packaging passed the Forge CI build on [run 39858077752](https://github.com/dylandlr/hearthbound/actions/runs/39858077752).

The mutation audit now emits:
- `session`: random UUID generated on Hearthbound JVM initialization; changes on restart.
- `observation`: fresh random UUID for each observed input consumption event.
- `worldName`: saved level name (not a persistent unique world identity).
- `dimension`, `pos`: server level and block position.
- `logicalTick`: current value of Hearthbound's server-wide SavedData clock.
- `input`, `consumed=1`, `outputs`: observed item deltas around Create's private processing method.
- `evidence=diagnostic_only researchCredit=false`: explicitly forbids inferring that rewards or scientific receipts are complete.

**Important limits:** the observation UUID is not a durable operation ID. Snapshot-based output deltas can still be incomplete, especially when inventory slot contents differ. This implementation does not capture verified recipe identity, persist mutation records atomically, or credit citizens. At the moment of a Create block-entity tick, `logicalTick` is the most recent completed logical server tick and should not be confused with an atomic per-event sequence number.

## Next gate
Verify that this commit compiles and packages; launch an EULA-authorized Forge server; inspect actual startup and injected Mixin behavior; then implement a durable exactly-once receipt pipeline with recipe identity and event ordinal.
