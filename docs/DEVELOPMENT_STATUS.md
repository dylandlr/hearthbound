# Hearthbound development handoff — 2026-10-14

Continue from `feature/first-mill-foundation`, reviewed in PR #4. This branch contains the autonomous Create production prototype. The separate `integration/verified-sable-hauling` / PR #26 is an earlier alternative controller implementation, not the latest First Mill implementation; reconcile its overlapping controllers before combining the branches.

## Implemented and checked

- Exact-source Java core suite, including 20,000 randomized ledger sequences.
- Full local Forge distribution build and seven JUnit tests.
- Genuine graphical Minecraft client, Forge 47.4.10 and Create 6.0.8.
- A reviewed 59.95-second screen capture on `61d51c0`: wheat 8 → 4, Sable physically supplies the mill, flour storage 0 → 2, production reaches its target, operator stops the order.
- On `67dd6c2`, assignment chooses the nearest eligible idle worker. Existing travel, cargo, and mill orders exclude workers from new manual jobs. Mill target/status/stop consistently choose the nearest worker with an order. Status includes the target.
- Added `scripts/worker-selection-probe.py` to the real Forge + Create CI sequence.
- Added resource-pack metadata to remove the client startup warning and corrected obsolete command messages.
- The updated build passed seven command-targeting assertions inside the real integrated Minecraft server.
- A subsequent Create CI run exposed a pre-existing route conflict on its three-block-wide elevated platform: Sable withdrew wheat and then fell away from the route. Colony jobs now suspend vanilla villager brain behaviors while owning navigation, then restore them after the final order/job ends. Normal navigation and physics remain enabled. On `ca623e5`, a fresh build/JUnit suite passed; the real client passed the seven selection checks again plus four narrow-platform checks, physically supplying wheat and delivering flour without falling. Dedicated Create CI then passed all production/target/stop scenarios; its new multi-worker fixture attempted assignment before its freshly loaded entity sections were visible. The fixture now verifies summon success and waits for both workers before issuing orders.

See [client evidence and provenance](REAL_CLIENT_PLAYTEST_2026-10-14.md) before making runtime claims.

## Next work

1. Improve visible navigation and station interaction. The prototype can step onto a millstone and wanders after becoming idle. It has no carrying animation.
2. Add explicit colony workshop ownership and shared-machine reservations before enabling general multi-worker production. Command selection alone does not provide machine ownership.
3. Add useful in-world order/status interactions and citizen needs once the production loop is stable.
4. Reconcile the two historical branch stacks before merging the final implementation to `main`.

This is a deterministic server-side controller. LLM/RL policies, crash-atomic cargo accounting, and multiplayer RTS territory gameplay are future work. Use disposable worlds and resources for tests.
