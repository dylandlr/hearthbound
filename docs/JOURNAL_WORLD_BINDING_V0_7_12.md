# v0.7.12 — World-bound research journals

ResearchJournalRuntime now requires a world UUID at construction and checks the journal ownership marker before opening either append-only file.

## Safety semantics
- A new binding is created only if both inbox and reward journals are absent.
- First creation returns RESTART_REQUIRED; caller must restart before opening journals.
- If journals exist but the binding is absent, fail closed (no automatic legacy migration).
- World UUID mismatches and corrupt bindings fail closed.
- Marker and journals must be in the same directory.
- Caller must source the UUID from persisted Overworld SavedData, not a new random UUID.

## What this DOES NOT prove
A sidecar marker is **not** a transactionally coupled header in each journal. Copying a marker together with a rolled-back world can still hide a rollback. There is no monotonic world checkpoint, startup reconciliation, cross-process lock, or late-taint handling yet. No gameplay research credits are enabled.

## Local unit test
```bash
javac --release 17 -d out src/main/java/dev/hearthbound/evidence/JournalWorldBinding.java src/test/java/dev/hearthbound/evidence/JournalWorldBindingTest.java
java -cp out dev.hearthbound.evidence.JournalWorldBindingTest
```
Nine standalone checks passed on Linux. The revised full runtime test and Forge build have not yet been run.

## Required next checks
- Run all standalone tests against the committed branch.
- Add binding to Forge server startup with authoritative world ID and journal readiness.
- Detect world/journal rollback via durable epoch/sequence checkpoints.
- Verify live Create callback and zero duplicate rewards across actual server restarts.
