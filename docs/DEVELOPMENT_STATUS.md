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
- Fixture readiness uses bounded `/data get entity ... Pos` queries, matching the production command's spatial lookup. It does not use `/say`, which produces no RCON feedback with no players connected. The full dedicated Forge + Create run `38656669350` passed on `2d852b9`, including every production scenario and the multi-worker fixture.

See [client evidence and provenance](REAL_CLIENT_PLAYTEST_2026-10-14.md) before making runtime claims.

## Gameplay review and current changes

Reviewed the full supplied recording; the [timestamped review](VIDEO_REVIEW_2026-10-14.md) separates baseline footage from current source. The production loop is real, but cargo visibility, workshop waiting behavior, and readable order progress need work.

On `929d8ab`, the full Forge build and seven JUnit tests passed in run [38671784669](https://github.com/dylandlr/hearthbound/actions/runs/38671784669). The exact-source core suite also passed, including 20,000 randomized ledger sequences.

The earlier restart staging failure was reproduced and traced to Minecraft's empty-server entity-idle gate after 300 ticks without players or forced chunks. The disposable acceptance arena now owns ticking tickets and explicitly tests assignment after a 20-second playerless idle period. Production hauling does not force chunks. Before the code change, a local baseline server with arena tickets successfully saved/restarted while carrying four wheat and delivered the same four after unblocking.

Hauling now requires a position beside each station and chooses supported, clear, reachable side approaches. Paths avoid climbing onto the target; a worker initially atop it can step off. Cargo remains in the existing persisted job if no approach exists. The real-world fixture records exact pickup/delivery positions and includes a worker starting atop the source.

Dedicated Forge run [38671784674](https://github.com/dylandlr/hearthbound/actions/runs/38671784674) passed normal hauling, side-position assertions, the atop-source approach, full-output preflight, post-pickup blockage, an actual save/restart with four wheat in transit, recovered delivery, and a later no-replay check. Source/cargo/destination were 4/4/0 after restart and 4/0/4 after unblocking. The prior restart verification gate is closed for graceful save/restart.

Production Forge + Create 6.0.8 run [38671784688](https://github.com/dylandlr/hearthbound/actions/runs/38671784688) passed registry/kinetic checks, genuine wheat grinding, citizen wheat supply and flour hauling, two autonomous flour deliveries, target/stop, and nearest-worker selection on the same source revision. No new graphical capture was made for this change; visual route quality remains a next-playtest task.


## Next work

1. Add visible cargo and brief station interactions, deriving presentation from existing persisted cargo without introducing another authoritative item inventory.
2. Give workshops a deliberate waiting location and readable in-world order progress; record the updated build from a closer camera. Server-side interaction-position assertions do not replace a fresh visual playtest.
3. Add explicit colony workshop ownership and shared-machine reservations before enabling general multi-worker production. Command selection alone does not provide machine ownership.
4. Add citizen needs and ordinary player-facing order controls once the production flow is readable.
5. Reconcile the two historical branch stacks before merging the final implementation to `main`.

This is a deterministic server-side controller. LLM/RL policies, crash-atomic cargo accounting, and multiplayer RTS territory gameplay are future work. Use disposable worlds and resources for tests.
