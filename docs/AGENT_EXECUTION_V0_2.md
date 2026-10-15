# Agent execution v0.2

`PolicyDecisionV02` binds a hierarchical task to the exact observation/world version used to select it. `DecisionGateV02` rejects stale or action-masked decisions before any mutation.

`MinecraftMillActionExecutor` is the server-thread bridge:

1. Re-read the current Minecraft observation.
2. Require an exact game-time/world-version match.
3. Require the task in the current server-authored action mask.
4. Recheck the work order is enabled and its persisted manager still has workshop access.
5. Reject new assignments while a haul or travel operation is active.
6. Delegate supply and collection to the existing reservation-safe `BarrelHaulController`.
7. Treat return as continuation of a verified flour delivery already carrying cargo.

The executor does not move items itself. Existing hauling dwell, navigation, reservation, capacity, persistence, and transfer checks remain the sole logistics implementation.

v0.2 uses strict same-tick freshness. A later asynchronous inference runner may replace this with a bounded revision token, but must not weaken server-side mask and authority validation.
