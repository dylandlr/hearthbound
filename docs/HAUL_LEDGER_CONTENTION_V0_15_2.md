# Hearthbound v0.15.2 — Concurrent hauling reservation acceptance

## Boundary: what exists now

The existing `HaulLedger` is an in-memory, synchronized Java state machine; it owns a `reservedSources` map keyed by source identity and UUID ticket receipts. States are RESERVED, IN_TRANSIT, COMPLETE and CANCELLED. This is a **logical reservation model** and does not guarantee Minecraft entity motion, world inventory conservation, persistence across crashes, or autonomous multi-citizen planning.

Earlier `HaulLedgerTest` checked eight sequential transitions. The seeded-C real Forge wheat-haul smoke failed once at 150 seconds, then passed on subsequent CI. The latest smoke instrumented timeouts and a deterministic fake-RCON path without changing real agent behavior. All eight workflows on commit `5d9213f` passed. The extraction to a shared RCON poll helper is tracked in PR #172 and was validated after correcting a stale test assertion.

## New concurrent stress tests

`HaulLedgerContentionTest` repeats a synchronized 16-citizen contention race **20 times**. Thread start order is not assumed. Each race checks:
- Exactly one citizen receives the reservation of a shared wheat chest.
- Fifteen simultaneous contenders are rejected; the ledger contains only one outstanding job.
- A stale cancellation cannot release an in-transit claim.
- An unauthorized second reservation cannot steal the source while its first haul is in flight.
- A completed claim releases the source exactly once; a different citizen can reserve it.
- A cancelled claim releases the source; duplicate cancellation is rejected, and the claim can be reused.

A second scenario launches 12 citizens reserving **different source chests** against a shared destination, verifying all 12 claims can coexist, their IDs are distinct, and all are released after valid transitions.

This test intentionally does not assert a particular winning citizen, since racing thread scheduling is nondeterministic. The invariant is source exclusivity, not deterministic thread order. Barrier wait timeouts ensure the test cannot silently pass when concurrency was not actually exercised.

## Acceptance and limits

The normal Java ledger CI now compiles and runs this new stress test along with the existing policy and ledger tests. No production `HaulLedger` source or Minecraft task authority is changed. Source inventory counts are not simulated here: a UUID reservation is not proof of physical item transfer.

Following successful CI, the next real Forge milestone is a **multi-citizen, physically instrumented competition fixture** with two or more villagers, a single stocked source, independently verifiable item counts, deliberate route blockage and unblocking, and explicit job/claim receipts. Such a test must not fake server inventory transitions or loosen existing timeouts. Actual server implementation should be informed by the current NPC command and task scheduler contracts before we script or expose new multiplayer actions.
