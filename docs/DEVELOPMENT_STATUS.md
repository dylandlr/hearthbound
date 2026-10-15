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

The reviewed 44.45-second continuous recording shows the actual controls and production. Exact revisions, runs, hashes and test staging are in [control evidence](WORKSHOP_CONTROLS_EVIDENCE.json); usage and boundaries are in [workshop controls](WORKSHOP_CONTROLS.md). That control-increment publication added documentation only; the later sharing changes are described below.

## Shared workshop increment

Millstones now keep an owner in dimension-scoped SavedData. Successful UI setup claims an unowned mill for the assigning player; other supervisors cannot bind it through their worker. Operators can authorize use without replacing the owner. Existing orders adopt their supervisor or server ownership.

Every hauling job now acquires its source and destination together before assignment. Other workers queue without creating cargo or taking stock. The saved lease identifies the worker and exact job, survives stop/pause/unload/restart, and ends after delivery or reconciliation of a completed/destroyed worker. Only ungranted requests can expire. The HUD reports shared-station waits and lost workshop access. Operator status/release commands expose ownership; release refuses a reserved mill.

The real Forge + Create test configures two workers against one mill and shared stockpiles, rejects a different owner's assignment without mutation, verifies acquisition has no partial lock, and checks discard cleanup. It stops and pauses the first worker after a genuine four-wheat pickup. After a full process restart, owner, cargo and the exact lease read from disk remain intact; the other worker has taken no stock. Resuming finishes the first delivery, and the second worker stores two flour and reaches its target with no remaining cargo or leases. A later check remains stable.

Final Java/resources are on `9956e61`. Later validation commits change only test scripts: real right-click retries for a moving idle worker, an arena ticking margin covering return paths, and readiness checks for saved entity sections. [Forge build/17 JUnit tests](https://github.com/dylandlr/hearthbound/actions/runs/38751846656) and the [core suite](https://github.com/dylandlr/hearthbound/actions/runs/38751846608) pass on `1f147df`. The [dedicated restart suite](https://github.com/dylandlr/hearthbound/actions/runs/38750870569) verifies a disk-restored reservation, four wheat, ten saved put-down ticks, delivery and no replay. The [full Create regression and shared-workshop restart](https://github.com/dylandlr/hearthbound/actions/runs/38751846524) pass with the final fixtures. The [actual graphical control regression](https://github.com/dylandlr/hearthbound/actions/runs/38751176563) passes setup, active edits, stop/resume, saved setup restart, target 2/2 and the 640×480 layout; the moving-worker open needed two genuine right-click attempts once.

See [shared workshops](WORKSHOP_SHARING.md) for behavior/recovery and [sharing evidence](WORKSHOP_SHARING_EVIDENCE.json) for exact source trees, runs and limitations. This continuation reviewed logs and automated assertions; it did not manually review a new video. The two-worker test is a genuine dedicated-server fixture, while the graphical regression covers the existing single-worker control flow.

## Native workshop status increment

The editor now has a separate **Status** page for the selected mill's owner/access and all three station reservations. It identifies the current holder, paused reservations, waiting counts and this worker's queue membership. Block picks can be inspected before Start without claiming a mill or creating a job. Back/Escape preserves the unsaved draft, and refreshes keep the status page open.

Status comes from a bounded server-to-client structure. Inspection checks build height, loaded chunks, station types and a 32-block worker radius before looking up station information. It reads the reservation queue without pruning it, and never mutates the order, cargo or ownership. Unknown/unavailable stations do not display a misleading empty queue. Online supervisors are named; offline owners receive an explicit generic label. The control channel is now protocol 2; install matching client/server builds.

Source `5963dc2` passes [Forge build and 21 JUnit tests](https://github.com/dylandlr/hearthbound/actions/runs/38764196349), [core tests and 20,000 randomized transfer sequences](https://github.com/dylandlr/hearthbound/actions/runs/38764196448), [dedicated cargo/reservation restart](https://github.com/dylandlr/hearthbound/actions/runs/38764196493), [complete Create/shared-workshop production and restart](https://github.com/dylandlr/hearthbound/actions/runs/38764196404), and [actual graphical control/status acceptance](https://github.com/dylandlr/hearthbound/actions/runs/38764196326).

The server compares worker and registry NBT before/after owner/stranger inspection and a paused other-worker/queued view; it also requires free/empty-queue status after completion. The UI-player probe rejects an unloaded preview without loading it. The graphical client renders an unclaimed preview before saving, preserves target 2 on return, renders an owned paused flour reservation after Stop, compares unchanged haul NBT, and completes Resume/restart/target. Both pages fit the native 640×480 window. New card foregrounds have calculated contrast ratios of at least 8.37:1. No new manual video review was performed with the local workspace disconnected.

See [workshop status](WORKSHOP_STATUS.md) for behavior and [status evidence](WORKSHOP_STATUS_EVIDENCE.json) for exact source trees, runs, archive digests, render witnesses and coverage limits. The publication after this source changes documentation only.

## Next work

1. Add explicit player-to-player sharing permissions and safe ownership-management controls to the native UI.
2. Review a two-worker graphical playtest and add runtime coverage for separate mills feeding one shared stockpile.
3. Add citizen needs once the multi-worker production flow and controls are readable.
4. Reconcile the two historical branch stacks before merging the final implementation to `main`.

This is a deterministic server-side controller. LLM/RL policies, crash-atomic cargo accounting, and multiplayer RTS territory gameplay are future work. Use disposable worlds and resources for tests.
