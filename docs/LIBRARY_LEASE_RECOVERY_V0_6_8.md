# Hearthbound v0.6.8 — Study lease lifecycle recovery

The Forge villager tick already invokes LibraryPolicyBridge.reconcile following
AutonomousLibraryStudy.tick and LibraryStudyRuntime.tick. This existed on the
branch before this patch (from another development session).

The change in this revision repairs the *restart* path:
- Library assignments persist their dispatcher UUID and acquired game tick.
- A still-active physical study job restores the same lease UUID in the
  in-memory dispatcher after a server restart.
- A finished or interrupted job releases ownership and clears the NBT lease.
- The CitizenWorkDispatcher regression now exercises idempotent restore,
  no duplicate assignment, proper release, and subsequent assignment.

CAUTION: This does NOT yet unify hauling and studying in one dispatcher.
The library bridge owns a static in-memory dispatcher; an authoritative
world-scoped dispatcher is still required for robust multi-world lifecycle and
load/unload behavior. Physical work must remain authoritative over claims.
Persisted NBT does not by itself authenticate reading content.

Acceptance checklist for actual Minecraft:
1. Auto-study an eligible marked primer; verify completion clears lease.
2. Interrupt study by removing the primer; verify subsequent new study possible.
3. Restart the server while traveling/studying; confirm the same lease restored.
4. No second assignment should start during a restored active job.
5. Confirm existing hauling controllers are unaffected.
6. Run policy-kernel GitHub Actions and Forge compile; record actual results.
