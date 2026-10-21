# Hearthbound v3.9 — Same-tick unified decision snapshots

Autonomous milling uses its one local ExperimentSelectionPolicy observation for actual decision and comparison. After physical job acceptance, ResearchTrainingRuntime samples CitizenLocalStateSensor at the current game tick and combines it with the already-observed research context using UnifiedObservationRuntime. The resulting independently versioned citizen (10) + research (11) domains are written under the physical job UUID to UnifiedDecisionSnapshotsSavedData.

Research and citizen values are gathered during the same server tick, but not in a transactional world snapshot: the research reading precedes job acceptance and the citizen-state reading follows it. Since the currently encoded citizen features exclude job ownership, this is expected not to change their values; future task-state features must use one read boundary.

Safeguards: reject differing snapshots for a given job, guard schema widths, preserve missing research domain without zeros, avoid loading chunks, and retain legacy 11-feature replay separately. Storage is bounded at 10,000 records per level and currently lacks pruning.

Limitations: no successor unified snapshot, no terminal decision, no migration to the old research transition record, no model training, no atomic cross-SavedData persistence. Tests are authored, but Forge compilation and in-game testing remain unverified.

Next: run the full test suite and Minecraft smoke; implement equivalent successor sampling and persistence with explicit availability flags and aligned schema before creating trainable (s,a,r,s',done) rows.
