# v0.7.6 — Persistent Hearthbound world identity

`HearthboundWorldIdentity` stores a single world UUID in Overworld `SavedData`. All dimensions resolve the same identity; `WorldIdentityCodec` is standalone Java 17 code with strict canonical parsing.

## Standalone test
```sh
javac --release 17 -d out src/main/java/dev/hearthbound/evidence/WorldIdentityCodec.java src/test/java/dev/hearthbound/evidence/WorldIdentityCodecTest.java
java -cp out dev.hearthbound.evidence.WorldIdentityCodecTest
```
Observed locally: PASS 9 checks.

## Safety and remaining integration gates
- This patch **does not install an event exporter, durable inbox, reward ledger or automatic research credit**.
- World identity is generated on first `SavedData` initialization and marked dirty. Marking dirty **does not guarantee fsync**. Do not emit durable research claims until the UUID's first save is verified on disk and restart-tested.
- If the data file is present but malformed, loading fails closed rather than silently minting a replacement identity.
- A completely missing identity file after a world rollback cannot be distinguished from first initialization by this class. Deployment must pair the identity with a persisted initialization marker and reject mismatched/rollback states before reward delivery.
- Need a Forge compile and dedicated server test of the 1.20.1 SavedData API and actual persistence through restart.
- Use `HearthboundWorldIdentity.get(level)` only from the authoritative server thread.
- PR #80's `exportVerified` already accepts an explicit UUID. Connect to this component only after the initialization fence above is enforced.
