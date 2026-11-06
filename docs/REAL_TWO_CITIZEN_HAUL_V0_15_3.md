# Hearthbound v0.15.3 — Two real Forge citizens, competing source claims

## Why the previous results are insufficient

The in-memory Java `HaulLedgerContentionTest` in PR #173 passed its concurrent single-source and independent-source invariants, and PR #172's real Forge smoke tests passed. Yet no test had assigned two **different real Minecraft villagers** to overlapping hauling work and verified the world-state consequences. The Java ledger and the real per-dimension `HaulClaims` are separate systems: the latter persists owner UUIDs in Minecraft SavedData and is called by the actual `SableHauling` runtime.

## Controlled test scenario

The standalone `scripts/rcon_two_citizen_haul_acceptance.py` and workflow `real-two-citizen-haul.yml` boot a fresh, disposable real Forge Minecraft world with the Hearthbound mod. They construct a simple flat testing surface with four actual chests (two with exactly eight wheat and two empty) and spawn **two genuinely separate marked Sable villagers**, at x=4 and x=22. Commands are executed at those positions so `SableController.nearestSable` selects the intended actor.

1. Citizen A requests a wheat haul from chest x=11 to x=7; the actual per-dimension source claim count must equal one.
2. Citizen B immediately requests a haul from the **same source** x=11 to a different destination x=19. The real server must reject the assignment with `source already claimed by another citizen`. This is not a mocked race and is intentionally sequential (the source claim persists while work proceeds).
3. Citizen B instead requests a different source x=24 to destination x=19; the real server must now have **two live source claims**.
4. Both real citizens must have `AUDIT job=...` receipts for their respective sources and show `claim=owned`.
5. Observe actual chest contents on the running server. Within 75 two-second polls, each destination must gain a wheat item; each source must drop from 8 to 7 and each destination rise from 0 to 1. This retains the same nominal 150-second acceptance budget as the single-citizen smoke.
6. Verify both durable source claims have been released and a marked citizen is physically near each destination. A command success or hauling ledger state alone never earns delivery credit.

The suite uploads the server log, Forge preflight output and complete RCON transcript for inspection. It also has fast fake-RCON regression tests that reject an accepted conflicting job, missing physical destination delivery and unreleased source claims. These mock contracts do **not** replace the dedicated-server test.

## Limits and next obstacles

This test validates independent citizen entity task execution and contention in the actual server but does not yet cover truly simultaneous command arrival across threads (Minecraft commands execute on the main server thread), physical route blockage, job preemption, citizen reproduction or multiplayer competition. The initial flat fixture is intentionally free of obstructed paths so source exclusivity and inventory conservation can be isolated.

Next, extend a separate held-out fixture with temporary physical route blockage, verify no item duplication and no unauthorized claim release during an obstruction, unblock the route, and require completion. We should only attempt that after the two-citizen real-world baseline passes. No new learned policies or LLMs are introduced.
