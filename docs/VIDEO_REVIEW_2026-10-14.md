# First Mill gameplay review

Reviewed the supplied `Hearthbound_First_Mill_Real_Minecraft(1).mp4` throughout its 59.95 seconds, using two-second frame samples and full-resolution status frames. The file is 1280×720 at 20 FPS, with no audio track. This is baseline build `61d51c0`, before the later navigation-ownership changes.

| Time | Observation | Implication |
| --- | --- | --- |
| 00:00–00:08 | Initial inventory checks and work-order commands occupy much of the screen. Sable starts outside the work area, then returns toward wheat storage. | The demo needs a clearer start state and an ordinary player-facing way to assign work. |
| 00:08–00:14 | Sable moves from the source to the mill, then drifts behind the work area. | Production is embodied, but competing wandering behavior makes the route look unfocused. Later navigation-ownership code must be evaluated separately. |
| 00:18–00:26 | Sable visits the mill and output barrel and stands on machinery. No cargo is visible. | Path targets should be accessible positions beside stations. Visible carrying and a brief interaction pose are still missing. |
| 00:30–00:34 | Debug inventory text shows two flour in output and four wheat remaining in the source. | The clip supports successful supply, real Create processing, and collection; it does not establish exact conversion accounting for all four withdrawn wheat. |
| 00:34–00:48 | Sable wanders away after production. The camera remains far away, with large areas of empty grass and sky. | A workshop waiting location and a closer camera would make intent and timing much easier to read. |
| 00:50–00:59 | Debug status confirms `TARGET_REACHED`; repeated counts remain four wheat and two flour, followed by an operator stop. | Target control works in this run, but there is no persistent, readable production interface. |

## What the clip establishes

The single-worker prototype runs inside actual Minecraft and completes a bounded production order. The scene is a technical acceptance test, not yet a representative colony gameplay experience. It does not demonstrate building the workshop, survival power, workshop ownership, multiple workers, recovery after restart, or a polished player interface.

## Priorities carried into implementation

1. Fix and verify the known blocked-cargo restart staging/recovery failure, with item conservation before and after an actual server restart.
2. Route workers to accessible positions beside stations, and prove those positions stay outside the station block.
3. Add visible cargo and meaningful interaction feedback without creating a second authoritative item inventory.
4. Give workshop orders a clear waiting location and readable progress display.
5. Record the updated build with a closer camera, labeled stations, and a clean player-facing start/end. Keep an uncut technical recording for verification.

The newer navigation-ownership and worker-selection fixes were tested separately in the preceding development session. The uploaded clip cannot prove their visual quality.

## Restart stall diagnosis

Reproduced the earlier fourth-scenario stall with the unchanged `9c7af5a` distribution on a real Forge 47.4.10 dedicated server. The worker remained alive at the same position with `Phase=DELIVER`, `Cargo=4`, `Result=CARRYING`, and no pause. Entity ticks stopped while world time and RCON continued. The arena had no forced chunks and no connected players.

Inspection of the installed Minecraft 1.20.1 `ServerLevel` bytecode confirmed the empty-server gate: after 300 ticks without players or forced chunks, entity processing is skipped. Adding tickets only to the disposable arena resumed the worker. The elapsed-world-time watchdog correctly reported a timeout after the diagnostic delay; resuming that test job then reached `OUTPUT_FULL_CARRYING` with source=4/cargo=4/destination=0.

After a real `save-all flush`, graceful shutdown, and fresh Java server process against the same world, `ci_restart_check` reported source=4/cargo=4/destination=0. Unblocking the barrel produced source=4/cargo=0/destination=4. This closes the baseline graceful-restart question; it does not establish crash-atomic accounting.

The fixture now owns persistent chunk tickets for its disposable arena and deliberately idles the playerless server for 20 seconds before assignment. Production hauling still requires loaded/ticking surroundings and creates no chunk tickets. Additional staging diagnostics distinguish entity-idle failures from pathfinding, pause, death, and destination blockage. Recovery also checks that the completed delivery remains stable after further ticks.

## Station navigation change

Hauling now chooses a reachable cardinal position beside its source/destination. Candidates need clear feet and head space, no fluid, a sturdy floor, and an already loaded chunk. Candidate paths must be complete and must not climb onto the target station; a worker initially atop it may step off. Extraction/insertion requires a nearby side position, navigation stops during transfer, and the worker faces the station. If no approach is available, cargo stays in the persisted job and the existing travel watchdog can pause it.

The real-world fixture records worker feet on the exact pickup and delivery ticks. Both normal hauling and a new scenario starting atop the source require side positions at both transfers. This establishes the interaction boundary; it does not yet establish the visual quality of the entire route or prevent an idle vanilla villager from wandering onto machinery later.

## Verification on `929d8ab`

| Check | Result | Evidence |
| --- | --- | --- |
| Exact-source Java core | Passed policy, watchdog, ledger, and 20,000 deterministic randomized sequences | `scripts/test-core.sh`, local and CI |
| Full Forge distribution and seven JUnit tests | Passed | [Forge Compile 38671784669](https://github.com/dylandlr/hearthbound/actions/runs/38671784669) |
| Empty-server dispatch and station approach | Passed normal transfer and a worker initially atop the source; both transfers occurred beside stations | [Dedicated server 38671784674](https://github.com/dylandlr/hearthbound/actions/runs/38671784674) |
| Full destination before/after pickup | No withdrawal into initially full output; in-flight cargo retained when output became full | Same dedicated-server run |
| Graceful save/restart and no replay | Restored source/cargo/destination=4/4/0; unblocked to 4/0/4; counts stable after further ticks | `HB_RESTART_PASS`, `HB_RESTART_DELIVERED`, `HB_RESTART_NO_REPLAY_PASS` in the same run |
| Production Forge + Create 6.0.8 | Passed real power/cutoff, grinding, citizen supply/flour delivery, two autonomous deliveries, target/stop and multi-worker selection | [Create runtime 38671784688](https://github.com/dylandlr/hearthbound/actions/runs/38671784688) |

The normal fixture observed pickup feet `(1,80,0)` and delivery feet `(8,80,0)` beside stations at x=2 and x=9. The atop-source fixture observed pickup feet `(2,83,-1)` and delivery feet `(8,83,0)`, proving it stepped to a side before extraction. These are real server observations, not a new graphical playtest. Visible cargo, a waiting location, a progress interface, and a new closer gameplay recording remain next work.
