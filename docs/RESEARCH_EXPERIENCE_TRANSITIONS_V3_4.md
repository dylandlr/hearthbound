# Hearthbound v3.4 — Explicit complete-transition contract

Adds `ResearchExperienceTransition` (schema v1) for offline datasets. Input is a causally verified reward record, the citizen's **actual predecision** observation vector, and an **explicitly measured post-outcome** observation vector with a successor tick. Missing observations cannot be synthesized from a mill receipt.

Action encoding for this first domain: 1=PROPOSE (executed physical experiment), 0=DEFER reserved for a future separate observational-learning dataset. The current verified-reward path only provides action 1.

A complete transition includes job/citizen UUIDs, decision tick, outcome tick, successor observation tick, evidence ID, numeric action, immutable state and next-state vectors, three reward components, and terminal flag.

## Important caveat
This adds a **contract and unit tests**, not end-to-end transitions. Current SavedData replay records do not contain either actual state vector; the physical mill execution path does not yet sample a successor observation or determine a defensible terminal condition. Do not mark complete solely because a reward arrived.

## Next work
- Persist predecision observations alongside pending job bindings.
- Capture successor observation with a time- and identity-bound server sensor after verified event; distinguish unavailable / terminal.
- Extend durable replay serialization using explicit migration from v1.
- Verify with Forge compilation, server restart tests, and multiseed physical Create scenarios.
