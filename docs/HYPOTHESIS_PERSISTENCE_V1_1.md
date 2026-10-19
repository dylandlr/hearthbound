# Hearthbound v1.1 — Persistent technology hypotheses

## Scope

Adds `TechnologyHypotheses.snapshot/restore` with fail-closed validation and `TechnologyHypothesisSavedData`, a per-dimension Minecraft `SavedData` store. This preserves each citizen's proposed, falsified or confirmed hypothesis through ordinary world saves, once the runtime calls this store.

The in-memory restore method validates all records before replacing the active map, rejects duplicates and malformed records, and preserves existing state when validation fails. The SavedData layer serializes the agent, recipe, expected input/machine/output, status and evidence ID.

## Important boundaries

- No technology unlocks or reward minting occur during load.
- `CONFIRMED` status is persisted but this layer does not revalidate event provenance on load; the trusted research coordinator must validate the original evidence before a transition to confirmed state.
- This layer is not yet connected to autonomous hypothesis generation or to the runtime's Create processing receipt callback.
- Forge/server smoke and restart acceptance remain required before declaring persistent in-game science demonstrated.

## Testing

`TechnologyHypothesisPersistenceTest`: exact snapshot restoration, duplicate entries rejected, corrupted status/evidence records rejected without partially modifying state.

## Next

Wire a verified Create receipt into the journal + hypothesis store using a recoverable, idempotent transaction. Add runtime commands strictly for observability, then a server-restart acceptance script confirming the hypothesis status and provenance survive.
