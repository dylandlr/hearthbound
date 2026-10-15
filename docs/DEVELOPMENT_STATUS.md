# Hearthbound development handoff — 2026-10-15

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


## Cargo and progress increment

The updated client renders wheat/flour at the worker's crossed arms and shows current activity, cargo count, actual flour stock and the target bar when looking at a worker. The server derives this display from existing cargo and stock; it does not equip another item stack. Build/ten JUnit tests, dedicated-server presentation/restart checks, and the full Create regression have passed. See [worker presentation](WORKER_PRESENTATION.md) for behavior and evidence. Source `9507e09` also passed the real graphical client check [38685271392](https://github.com/dylandlr/hearthbound/actions/runs/38685271392). The delivered 43-second recording shows held wheat/flour, cleared cargo after delivery, and actual flour stock 2/2 with a full target bar. The upper-left card stays clear of chat. Current full Forge build, dedicated restart and Create production runs all pass; exact provenance and client render assertions are recorded in [the presentation evidence](WORKER_PRESENTATION_EVIDENCE.json). The test observer follows by teleporting; the worker uses normal navigation. A flour haul is briefly paused for its visual assertion and then resumed.

## Workshop routine increment

Work orders now save a clear, supported waiting point. `/hearthbound mill_order_wait <x> <y> <z>` changes it for the nearest ordered worker. Idle workers return while milling or at their target, report an obstructed point, retry after clearing it, and immediately yield to a new haul. Return navigation checks station avoidance and can use floor waypoints around the machines. Stopping scheduling leaves an active haul intact.

Pickup and put-down now dwell for 15 server ticks beside a station before the existing inventory transfer. Remaining dwell is saved with the haul. The card names each interaction and the cargo visual reaches slightly forward/lower during put-down. See [workshop routine](WORKSHOP_ROUTINE.md) for the behavior, controls and acceptance coverage.

The first runtime pass on `52f0acf` passed the build/core suites, dedicated 15-tick interaction and partial-dwell restart checks, and the real graphical client. Create production completed two flour deliveries, then exposed a return-path choice over station blocks; it was correctly rejected but prevented a valid floor return. `d895607` adds checked floor detours. The original edge-point test then exposed a second issue: one-second arrival samples could miss a whole tile and make the worker reverse repeatedly. Actual position/motion traces established the overshoot; `230d518` checks final/turn arrival every tick while retaining once-per-second pathfinding and watchdog sampling. The unchanged edge-point test now passes, including changing points, head obstruction, automatic retry and stable inventory counts.

Final source `230d518` passes [build/ten JUnit tests](https://github.com/dylandlr/hearthbound/actions/runs/38690073104), [core suite](https://github.com/dylandlr/hearthbound/actions/runs/38690073119), [dedicated partial-dwell restart](https://github.com/dylandlr/hearthbound/actions/runs/38690073111), [Create production/waiting/selection](https://github.com/dylandlr/hearthbound/actions/runs/38690073133), and [actual graphical client](https://github.com/dylandlr/hearthbound/actions/runs/38690073141). The delivered 34.5-second continuous production excerpt shows real milling waits, flour transport and final return to the yellow tile at stock 2/2. It comes from the 46.5-second raw client capture, with observer following and a brief test pause for the first flour assertion. Exact source/JAR/video provenance and render witnesses: [workshop evidence](WORKSHOP_ROUTINE_EVIDENCE.json).

## In-game controls increment

Empty-hand right-click now opens a native First Mill screen. Players select stations and a waiting floor block in the world, type a target, and start without server commands. Active targets/waiting spots can be saved; Stop preserves the current haul and cached setup, Resume retries a paused haul, and an explicit later Start reuses the setup. The first successful assignment binds a supervisor; another player can inspect, while the supervisor and operators can edit. Server sessions resolve exact worker UUIDs and reject stale revisions, wrong workers, invalid/unloaded stations and unauthorized edits before mutation. Worker supervision does not reserve shared machines.

Gameplay `3fd0c48` passes the real Create regression and [actual non-operator graphical click-through](https://github.com/dylandlr/hearthbound/actions/runs/38694479221), including target 3→2, stop with unchanged flour cargo, disabled Start, UI resume, cached restart and final target 2/2. The 640×480 native layout is verified. `024ba00` changes the dedicated test ordering only and passes build/thirteen JUnit tests, core tests, the original empty-server/cargo/restart/no-replay regression, and missing-Create air rejection. The UI test initially missed a moving worker after delivery; the observer now follows while opening, as it already did for presentation checks. No worker is teleported.

The reviewed 44.45-second continuous recording shows the actual controls and production. Exact revisions, runs, hashes and test staging are in [control evidence](WORKSHOP_CONTROLS_EVIDENCE.json); usage and boundaries are in [workshop controls](WORKSHOP_CONTROLS.md). No source or resource change follows the captured build; the final publication adds documentation only.

## Next work

1. Add explicit workshop ownership and shared-machine reservations to complement per-worker supervisor permissions.
2. Verify two independently managed workers sharing machines and stockpiles under reservations before general multi-worker production.
3. Add citizen needs once the production flow and order controls are readable.
4. Reconcile the two historical branch stacks before merging the final implementation to `main`.

This is a deterministic server-side controller. LLM/RL policies, crash-atomic cargo accounting, and multiplayer RTS territory gameplay are future work. Use disposable worlds and resources for tests.
