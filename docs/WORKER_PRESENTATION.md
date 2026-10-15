# Worker cargo and production progress

Updated clients show a colony worker's carried wheat or Create flour at the villager's crossed arms. Look at the worker from nearby to see a compact card in the upper-left corner with the current activity, carried quantity, and the actual flour stockpile count. Orders with a finite flour target also show that target and a progress bar. Open menus and the hidden-GUI setting hide the card.

| Situation | Card activity |
| --- | --- |
| Walking to collect input or finished flour | Collecting supplies |
| Carrying goods to a station | Delivering cargo |
| Station dwell before extraction | Picking up supplies |
| Station dwell before insertion | Putting down cargo |
| No active haul, returning to saved floor position | Returning to waiting spot |
| Saved waiting point is obstructed or unreachable | Waiting spot blocked |
| Destination has no room | Storage full |
| Travel watchdog paused the haul | Hauling paused |
| Create is processing supplied wheat | Waiting for the mill |
| Stored flour meets the order target | Flour target reached |
| Workshop chunk is unavailable | Waiting for the workshop to load |

The bar counts flour physically stored in the order's output barrel. It excludes goods still being processed or carried. The target remains a scheduling threshold; existing batches and in-flight jobs retain their prior behavior. An unlimited order shows its stored flour count without a target bar.

## State and resource boundary

`WorkerPresentation` reads the existing persisted haul, work order, and loaded stockpile. It never withdraws, inserts, equips, or drops an item. A clientbound packet contains the worker's entity ID, UUID, dimension, item identifier, count, activity, and stock/target values. A temporary client render stack is used only for drawing; server equipment and resource accounting remain unchanged.

Tracking players receive an initial snapshot and subsequent changes at most every five entity ticks, with a five-second heartbeat. The client checks dimension and UUID before using an entry and clears entries when entities/levels leave or the connection closes. Server work remains authoritative; no inventory action is accepted from the client. Client and server need the updated Hearthbound build for the presentation channel.

The explicit `/hearthbound_client_view` diagnostic reports received state plus item-layer and HUD frame counts for the worker under the crosshair. `/hearthbound worker_view` reports the server's derived snapshot. Ordinary viewing needs neither command.

## Validation

- Source `46781f3`: full distribution build and ten JUnit tests, including three packet round-trip cases (flour, full cargo/unavailable storage, and clearing state).
- Dedicated Forge [38673779241](https://github.com/dylandlr/hearthbound/actions/runs/38673779241): presentation agrees with authoritative wheat cargo; equipment remains empty; full-output handling, side approaches, actual restart, recovered delivery, and no replay pass.
- Production Forge + Create [38674073403](https://github.com/dylandlr/hearthbound/actions/runs/38674073403): in-flight flour appears in the derived view; target display matches the real stockpile; the complete production and worker-selection regression passes. `f81ab6f` changes workflow coverage only.
- Source `9507e09`: [full Forge build](https://github.com/dylandlr/hearthbound/actions/runs/38685271319), [dedicated restart/hauling](https://github.com/dylandlr/hearthbound/actions/runs/38685271328), [Create production](https://github.com/dylandlr/hearthbound/actions/runs/38685271431), and [real graphical Minecraft check](https://github.com/dylandlr/hearthbound/actions/runs/38685271392) all pass. The client is a separate production Forge process connected to the dedicated server, not an integrated-server shortcut.

## Recorded client evidence

The delivered `Hearthbound_Cargo_Progress.mp4` is 43 seconds, 1280×720 at 20 FPS, with no audio. It is a continuous capture of the actual X11 Minecraft window, with no generated frames or time acceleration. Its container was remuxed for streaming without re-encoding. Source, installed JAR hash, delivered video hash and exact client diagnostic lines are in [the evidence record](WORKER_PRESENTATION_EVIDENCE.json).

| Client state | Cargo-layer frames | HUD frames | Visual review |
| --- | ---: | ---: | --- |
| Storage full, four wheat retained | 43 | 29 | Wheat visible at crossed arms; amber card says carrying 4 wheat. |
| Delivery completed | 0 | 41 | Held item clears; card says ready for work. |
| One flour carried | 137 | 124 | Actual Create flour visible; card shows carrying 1 wheat flour and stock 0/2. |
| Flour target reached | 0 | 43 | Empty hands; stock 2/2 and full green bar. |

Reviewed full-resolution key frames and three-second samples throughout the clip. The observer player is teleported to follow Sable; the worker is never teleported. The first flour job is temporarily paused through its persisted test state to hold the visual assertion, then resumed to complete the same delivery and work order. Blocks, starting resources, and creative-motor power are staged by the test. Debug diagnostics and the earlier fixture are visible; this is a development acceptance recording, not a polished gameplay trailer.

The code creates no additional server equipment or dropped cargo. The dedicated inventory tests and the graphical check confirm source=4/destination=4 after the four-wheat transfer. The real Create order then produces and stores two flour and reports its target reached.

## Workshop routine follow-up

Source `230d518` adds saved waiting points, checked floor detours, per-tick arrival detection, and 15-tick pickup/put-down feedback. Its full Forge build, core suite, dedicated partial-dwell restart, Create production/waiting regression, and real graphical client all pass. The new 34.5-second delivered excerpt shows the production routine and return to the saved tile. See [workshop routine](WORKSHOP_ROUTINE.md) and its [separate evidence record](WORKSHOP_ROUTINE_EVIDENCE.json); the older 43-second capture above retains its original source and provenance.

## Remaining gameplay work

A saved waiting location and brief station interaction feedback are implemented; see [workshop routine](WORKSHOP_ROUTINE.md). Work assignment is now available through the native [workshop controls](WORKSHOP_CONTROLS.md). Workshop ownership and machine reservations are required before general multi-worker production. The new item visual does not add an animation system, citizen needs, or learned policies.
