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
