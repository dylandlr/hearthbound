# In-game workshop status

Empty-hand right-click a colony worker, then press **Status** in the editor's upper right. **Back to setup** or Escape returns to the same unsaved draft. Opening the page does not start, stop, claim or reserve anything.

The page shows the selected mill's owner and the inspecting player's access. Your mills display **You**; server-owned mills display **Server**; another connected supervisor displays their name. An offline supervisor is labelled as another supervisor rather than given a guessed name. Access to the worker and access to the mill remain separate permissions.

Three station cards show the server-inspected coordinates, whether the station is available, and which worker holds its reservation. A holder outside the server's loaded entities is shown as a worker away. Paused reservations are identified. Each card shows how many live requests are waiting and whether this worker is queued. A request for a two-endpoint haul can appear on both endpoint cards. Counts are capped at 999; they are not queue positions or inventory quantities.

The page refreshes once per second while open. A paused or absent holder retains its reservation. An unavailable, missing, wrongly typed or distant station displays an inspection hint rather than implying its queue is empty. Long labels have full-text hover tooltips. The separate page keeps the original order editor usable in a 640×480 window at GUI scale 2.

## Draft inspection and authority

Picking a block refreshes its public status before an order is started. Preview coordinates use the existing authenticated worker session. Each inspected coordinate must be within build height, already loaded, within 32 blocks of the worker, and the correct barrel/millstone type. Inspection does not force a chunk to load, claim a mill, edit a work order, modify cargo, or acquire/cancel a reservation. Expired pending requests are excluded from the display without pruning the live queue.

The client receives a separate bounded status structure alongside the existing snapshot. It contains public owner/access and station metadata, with inspected coordinates; it contains no inventory. The server still checks current supervisor, session, range, revision and mill access when an actual mutation is requested.

The workshop control channel is now protocol **2**, because the server-to-client snapshot gained structured status. Client and server need the matching build.

## Verification

Unit coverage includes complete snapshot round trips with worker identity/settings, negative station coordinates, holder/paused/queue metadata and bounded labels/counts. Standalone reservation checks verify that status reads neither prune pending requests nor change active leases.

The genuine shared-workshop server fixture inspects another worker's paused reservation and queue, checks owner/stranger access, and compares worker and registry NBT before/after inspection. It verifies released stations show available with no waiting request after production. The connected UI-player probe also tries an unloaded preview and requires the chunk, worker and registry to remain unchanged.

The genuine graphical client opens an unclaimed preview before saving, checks there is still no owner or reservation, returns to the unsaved target of 2, and starts through the normal screen. Later it opens the status page while carrying paused flour after stopping its order, renders the owned paused reservation, returns, and compares the complete haul NBT. The existing resume/restart/target flow remains required. Both native pages are checked at 640×480, including space between the status footer and Back button.

The workflow records render witnesses and screenshots. A local manual review of the new recording was unavailable during this continuation. This page supplies inspection; explicit player-to-player sharing permissions and ownership-management buttons remain follow-up work.
