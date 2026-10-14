# Testing gates and honesty checklist

## Verified
- GitHub Forge compilation succeeded on the ancestor fix/forge-compilation-errors branch (run 38628512004).
- Pure Java policy CI completed on earlier branches.

## Newly introduced
- A deterministic reservation ledger prototype. It prevents competing assignments for the same *logical source key* while its process remains alive.
- A dependency-free regression workflow covering state transitions, replay rejection, and reservation release.

## Not yet integrated or verified
- Ledger is NOT wired into SableHauling. No claim of duplicate-safe physical inventory transfers.
- The ledger is in memory only. No recovery from process restart, no transactional disk storage.
- No real Forge server/client boot, GameTest, multiplayer gameplay or video captured.
- For real game E2E, ensure Minecraft boots, Sable spawns, two chests exchange exactly one wheat, output-full cases pause safely, and restart cases conserve item counts.

## Next steps
1. Persist ledger in Minecraft SavedData with explicit data versioning.
2. Define atomic-ish write-ahead phases, reconciliation rules and failure injection points.
3. Wire one source-key reservation per job to SableHauling.
4. Add Minecraft GameTests and dedicated server smoke check, *then* record actual gameplay.
