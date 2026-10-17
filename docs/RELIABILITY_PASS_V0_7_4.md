# Hearthbound v0.7.4 — scheduler reliability pass

This revision fixes two independent lifecycle defects:

1. CitizenWorkDispatcher now retains only the most recent 256 decisions.
   Earlier entries are evicted rather than allowing unbounded process memory
   growth. CitizenWorkDispatcherTest checks 300 rejected dispatches and
   asserts the precise earliest/latest retained observation versions.
2. LibraryStudyRuntime stores lastProgressTick with the physical reading
   session, and does not advance reading twice within one server game tick.
   This protects against duplicate event subscriptions and related replay
   paths. The check is persisted with the session NBT.

## Remaining verification
- Compile and run policy-kernel workflow on GitHub (not confirmed).
- Forge compile with Create dependency and run the Minecraft client/dedicated
  server (not confirmed).
- Verify server restart during reading, a duplicate tick event, and missing
  marked primer never award excess knowledge.
- Test HAUL -> FREE -> STUDY -> FREE with inventory conservation and proper
  source reservation teardown.
- Check that physical ownership conflict records are surfaced and fail closed.
- Real health/needs observation and world-scoped dispatcher are still pending.

The execution environment could not resolve github.com directly via git;
files were instead modified using the connected GitHub integration.
