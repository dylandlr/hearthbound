# Workshop waiting and station interactions

A First Mill work order saves a waiting spot beside the workshop. Sable returns there whenever no haul is active, including while the mill processes wheat and after the flour target is met. A ready production job takes priority over the return trip. Normal entity movement and physics stay enabled.

New orders use the worker's current safe floor position when possible, otherwise a clear location near the mill. Existing saved orders acquire a default on their next idle tick. An operator can change the nearest ordered worker's spot with:

```
/hearthbound mill_order_wait <x> <y> <z>
```

The coordinates identify the worker's feet, above a supported floor. The point must be loaded, clear at feet and head, within 32 blocks of the mill, and away from station blocks and their immediate interaction sides. Navigation paths must avoid climbing over the workshop's three stations. If vanilla pathfinding prefers a route over a machine, the waiting controller tries floor waypoints outside the station bounds; each leg must have a complete checked path. This is a small workshop detour, not a general maze planner. `/hearthbound mill_order_status` reports the saved coordinates and waiting state.

An obstructed point stops the worker and reports “Waiting spot blocked.” Sable retries every two seconds; clearing the obstruction lets her return. An unloaded destination waits for its chunk without forcing it to load. Unreachable routes use the existing progress watchdog and retry. Waiting never moves items or owns cargo. Stopping an idle order stops its return path; stopping during a haul preserves that job and its cargo.

## Station interaction

On reaching a valid side of an inventory, Sable stops, faces it, and spends 15 server ticks picking up or putting down supplies. The card shows the corresponding activity. During put-down, the held visual moves slightly forward and lower. This extends the vanilla crossed-arm cargo layer; it does not replace the villager model or add a skeletal animation system.

The dwell's phase and remaining ticks are saved in `HearthboundHaul`. Inventory eligibility and destination capacity are checked again before transfer. Cargo stays in the source during pickup and in the saved job during put-down, then the normal transfer commits. Leaving reach or losing access resets the dwell; pausing preserves it. A graceful save/restart can resume the remaining interaction. This does not establish crash-atomic inventory/entity saves.

Navigation/watchdog samples remain once per second, while interactions update every five ticks. Waiting-point and detour-turn arrival are observed every tick so a worker stops while entering a tile instead of passing through between samples. Presentation packets keep their existing schema. The visual reach uses elapsed client time since the activity arrived; it is cosmetic, not another transfer clock.

## Acceptance coverage

- Dedicated Forge observes the exact pickup/delivery ticks, requires at least 15 ticks of dwell and a position beside each station, checks conservation and empty equipment, and exercises full output before and after extraction.
- Restart fixture clears a blocked output, lets the real put-down begin, then pauses the job with ten interaction ticks remaining. It flushes and restarts the same world, verifies the saved phase/count/timer, resumes, and checks delivery and no replay.
- Production Create regression verifies physical return, rejects an occupied station as a waiting point, blocks a distant point's head space before arrival, checks the blocked card, clears it, and verifies automatic retry and stable stocks.
- Separate graphical client follows the normally navigating worker, records actual HUD/item render witnesses for short interactions and the return journey, and checks its final position on the saved yellow waiting tile. The observer camera is teleported; Sable is not. The first flour job is briefly paused for a stable visual assertion, then resumed.

## Verified revision and recording

Source `230d518` passes the [Forge distribution build and ten JUnit tests](https://github.com/dylandlr/hearthbound/actions/runs/38690073104), [core suite](https://github.com/dylandlr/hearthbound/actions/runs/38690073119), [dedicated interaction/restart regression](https://github.com/dylandlr/hearthbound/actions/runs/38690073111), [complete Create production and waiting regression](https://github.com/dylandlr/hearthbound/actions/runs/38690073133), and [separate graphical client check](https://github.com/dylandlr/hearthbound/actions/runs/38690073141).

The delivered `Hearthbound_Workshop_Routine.mp4` is a continuous 34.5-second excerpt, starting 12 seconds into the original 46.5-second capture. It shows wheat delivery, waiting while the mill works, flour pickup/delivery, and the final return to the saved yellow tile with actual stock 2/2. Exact trimming re-encodes the original frames at 1280×720/20 FPS, with no audio or time acceleration. The full capture and diagnostics remain in the graphical workflow artifact. Source/JAR/video hashes, diagnostic lines and test results are in [the evidence record](WORKSHOP_ROUTINE_EVIDENCE.json).

Reviewed full-resolution target imagery and three-second samples across the capture and excerpt. Rear camera angles sometimes hide the crossed-arm item behind the villager's body. Diagnostics remain visible; this is development acceptance footage. Player-facing controls, workshop ownership and machine reservations remain the next product work.
