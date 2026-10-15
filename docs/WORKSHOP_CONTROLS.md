# In-game workshop controls

With an empty main hand, right-click a colony worker to open First Mill setup. Choose the wheat barrel, Create millstone, flour barrel, and an optional waiting spot by pressing each button, then right-clicking the matching block in the world. Waiting points use the top face of a floor block. Escape returns from picking to the same draft.

Enter a flour target from 0 to 4096; zero means unlimited. Start order saves the setup and begins the existing production scheduler. The screen shows current activity and actual stored flour. Close or Escape from the screen discards unsaved edits. Holding an item leaves ordinary entity interactions available.

While an order is active, Save changes updates its target and waiting point. Stop order stops scheduling; the existing haul finishes with its cargo intact. Start stays disabled while that haul is active. A paused haul exposes Resume haul, including after stopping its order. This retries the same saved cargo and phase. The last setup remains available for another explicit Start after completion. Change station bindings after stopping and finishing the current job.

## Supervisor and server rules

The first successful UI assignment of an unowned idle worker saves the assigning player's UUID as supervisor. That player or a server operator can manage the worker. Other players can inspect the screen. Unowned workers with existing command-managed jobs require an operator; opening a screen never claims a busy worker. Supervisor identity and the reusable setup are saved on the worker.

The screen uses a separate client/server control channel. Every mutation resolves the exact worker UUID in the sender's current dimension and requires a session opened within six blocks with line of sight. Editing/picking can continue within 32 blocks. Every mutation checks session, supervisor, build ability, range and order revision. Saving also checks loaded blocks, station types and target range. It never loads a posted station coordinate to validate it. A concurrent command or another valid edit changes the revision; stale saves and stops are rejected with the current settings.

Picking is an unsaved client draft. Only explicit Start/Save/Stop requests change the order. An active order's station bindings cannot be replaced. Hauling owns the only transferable cargo, and stopping never erases it. The setup cache contains configuration, not an active job or another inventory. Existing operator commands use the same order mutations and revision counter.

Supervisor permission applies to workers. It does not reserve barrels or Create machines, establish colony territory, or integrate third-party land claims. Workshop ownership and shared-machine reservations remain the next multiplayer foundation.

## Verification

The tests include supervisor/operator access and bounded request round trips, the existing dedicated-server cargo/restart suite, and the complete Create production/waiting/selection regression.

The graphical acceptance test uses a separate actual Minecraft client and server. xdotool right-clicks the worker, clicks native buttons, selects four world blocks, cancels a pick with Escape, types the target and starts as a non-operator. A server probe uses that real player's active session to reject stale, wrong-worker, invalid-target, unloaded-point and stranger requests without changing cargo or the order. The client then stops while carrying real flour, checks unchanged haul NBT and disabled Start, resumes the retained haul through the screen, lets delivery finish, and restarts the cached setup through the screen to reach its target.

The graphical test also changes an active target from 2 to 3 and back and inspects the native screen in a 640×480 window.

## Verified builds and capture

Gameplay source `3fd0c48` passes [production Forge + Create](https://github.com/dylandlr/hearthbound/actions/runs/38694479661) and the [real graphical click-through](https://github.com/dylandlr/hearthbound/actions/runs/38694479221). Revision `024ba00` changes only the dedicated probe's ordering, preserving the earlier empty-server-idle regression before adding any optional-Create fixture ticket. Its [Forge build and thirteen JUnit tests](https://github.com/dylandlr/hearthbound/actions/runs/38694976723), [core suite](https://github.com/dylandlr/hearthbound/actions/runs/38694976792), and [dedicated restart/optional-Create checks](https://github.com/dylandlr/hearthbound/actions/runs/38694976592) all pass. Java and resources match the captured build.

The delivered `Hearthbound_Workshop_Controls.mp4` contains 44.45 seconds of continuous actual Minecraft at 1280×720/20 FPS, silent. The recorded stream was remuxed for streaming without changing its encoded video. Setup, active target edits, production, stop/resume, restart and final return are visible. Native small-window validation occurs after the recording and is preserved in the workflow screenshots.

Reviewed full-resolution configured/stopped/small-window images and four-second samples through the recording. Text and button states are readable, including disabled Start during an unfinished haul and the Resume button. Source/JAR/video hashes, supervisor checks and exact UI witnesses are in [the evidence record](WORKSHOP_CONTROLS_EVIDENCE.json). The observer follows by teleporting; Sable is never teleported. Starting resources and creative-motor power are staged. The first flour haul is deliberately paused for the stop/recovery assertion, then resumed using the actual screen.

Client and server need the matching Hearthbound build for the control channel. The interface uses Forge's native [Screen API](https://docs.minecraftforge.net/en/1.20.1/gui/screens/) and [main-thread packet handling](https://docs.minecraftforge.net/en/1.20.1/networking/simpleimpl/).
