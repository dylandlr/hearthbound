# Hearthbound v3.8 — Unified, versioned citizen observation envelope

Adds a read-only `UnifiedCitizenObservation.Snapshot` containing the same citizen UUID and game tick, with independent citizen-state (v1, 10 features) and optional research-context (v1, 11 features) domains.

The citizen-state domain is mandatory, while research context is explicitly absent unless a valid research observation was captured. Missing research is never substituted with an all-zero vector. `flatForResearchModel()` only yields a deterministic 21-wide vector when both domains were genuinely observed.

This is a **schema and pure combination primitive**. Minecraft runtime sampling of both domains on the same tick, SavedData persistence of combined observations, successor alignment, action masks, schema migration, training and performance evaluation still require implementation. Individual local sensor measurements are distinct from actual hunger/shelter physiology or learned genetic attributes.

Tests cover schema boundaries, optional context, defensive copies and deterministic width. Forge CI and live game verification are pending.
