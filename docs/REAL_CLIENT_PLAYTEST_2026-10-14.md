# First real graphical Minecraft playtest

## Recording provenance

- File: `Hearthbound_First_Mill_Real_Minecraft.mp4`, delivered with this development session.
- Capture: actual X11 Minecraft window, 1280 × 720, 20 FPS, 59.95 seconds. Continuous screen capture, no time acceleration or generated frames. The MP4 container was remuxed for streaming; the captured video stream was copied unchanged.
- Minecraft 1.20.1; Forge 47.4.10; Create 6.0.8; Java 17.0.20; Mesa llvmpipe software graphics.
- Hearthbound source: `61d51c0d5b706458ded2a1a7137d8f7f285b8104`.
- Built artifact: `hearthbound-forge-dev-jar`, Actions run `38617494483`, artifact `11920866090`.
- Installed Hearthbound JAR SHA-256: `e93f2a69531dd44662bcdcfd6f79a09de86f8f55c4803b8a85db7d5c47278403`.
- Delivered MP4 SHA-256: `d4b4bee9c176b49fde057e870c8ed24bf252c0152d970a5d9c5e659a0ef41f5c`.
- Sound playback used a null output device. The recording has no audio track.

## Observed behavior

A disposable Creative superflat world was staged with two vanilla barrels, a real Create millstone, and a test-only creative motor underneath the mill. Commands placed the initial blocks and eight wheat in the source. Production itself used a single First Mill order; there were no direct inventory-transfer commands during the recorded production sequence.

| Check | Observed result |
| --- | --- |
| Baseline source barrel | 8 wheat |
| Baseline flour barrel | Empty |
| Wheat supply | Sable walks from source toward the mill; source becomes 4 wheat |
| Real Create production | Powered millstone grinds the supplied wheat |
| Flour collection | Sable moves between mill and output storage; storage becomes 2 flour |
| Production target | `mill_order_status` reports `TARGET_REACHED`, hauling `IDLE` |
| Stable target | Repeated inventory inspection still shows source 4, flour 2 |
| Operator stop | `First Mill scheduling stopped; existing haul retained.` |

The target is a stockpile scheduling threshold. A batch of four wheat was supplied even though the flour target was two. The clip does not establish exact wheat-to-flour mass accounting or prove that two remaining wheat were unprocessed.

## Code changes after the recorded build

`67dd6c227447468ddfc2e13a35415d8ce967ec72` fixes nearest-worker assignment and management, adds the real-server multi-worker regression, and supplies missing `pack.mcmeta` metadata. The gameplay clip uses the preceding build; do not describe it as footage of the new worker-selection code.

The new source passed `gradle --no-daemon build` locally: seven JUnit tests, zero failures/errors. The exact-source standalone suite also passed, including 20,000 deterministic randomized transfer sequences. Local build JAR SHA-256: `f7f0605b2df97a3894ecde4491b99978eabb603c0e99243831317d417af69a75`.

The same JAR was launched in the graphical client and its integrated server passed seven additional assertions: nearest worker receives the first order, an already assigned worker is skipped, each of two workers receives its own target, stopping the nearer order retains the farther order and target, and busy workers reject a new order. Log marker: `HB_WORKER_SELECTION_CLIENT_PASS 7/7`.

Create dedicated-server CI on this revision failed during physical delivery on its narrow elevated platform: the worker left the platform after pickup. This is separate from the successful wide-platform client recording. The follow-up navigation-authority change suspends vanilla villager behavior while colony jobs run; its validation must be recorded separately.

## Limits

This is prototype evidence, using deterministic rules, a vanilla villager body, a disposable test scene, and a creative motor. It does not prove survival power construction, general multi-worker resource arbitration, graceful or crash-restart conservation, multiplayer playability, carrying animations, or LLM/RL decision-making. Movement and station interaction need polish.
