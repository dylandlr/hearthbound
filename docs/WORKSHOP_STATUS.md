# In-game workshop status and access

Empty-hand right-click a colony worker, then press **Status** in the editor's upper right. **Back to setup** or Escape returns to the same unsaved draft. Opening the page does not start, stop, claim or reserve anything.

The page shows the selected mill's owner and the inspecting player's access: owner, shared collaborator, operator, denied or unclaimed. Your mills display **You**; server-owned mills display **Server**; another connected supervisor displays their name. Offline owners and collaborators use generic labels rather than guessed names. Access to the worker and access to the mill remain separate permissions.

Three station cards show the server-inspected coordinates, availability and reservation holder. A holder outside the loaded entities is shown as a worker away. Paused reservations are identified. Each card shows how many live requests are waiting and whether this worker is queued. A two-endpoint request can appear on both endpoint cards. Counts are capped at 999; they are neither queue positions nor inventory quantities.

The page refreshes once per second. An unavailable, missing, wrongly typed or distant station displays an inspection hint rather than implying its queue is empty. Long labels have full-text hover tooltips.

## Access controls

Mill owners and server operators can press **Access**. The page cycles through current collaborators and eligible connected players. **Share** grants the selected online player access; **Revoke** removes an existing grant. A mill can have up to eight collaborators.

**Release ownership** clears the owner and all grants. It remains disabled while a haul reserves the mill, including paused and absent workers. Revoking or releasing does not erase cargo, active reservations or work-order data. Existing unauthorized orders stop before scheduling their next haul.

The server resolves player UUIDs from its own bounded snapshot and rechecks current owner/operator authority for every mutation. The client never posts a player name, owner record, inventory or NBT.

## Draft inspection and authority

Picking a block refreshes its public status before an order starts. Preview coordinates use the authenticated worker session. Each inspected coordinate must be within build height, already loaded, within 32 blocks of the worker, and the correct barrel/millstone type. Inspection does not force a chunk to load, claim a mill, edit an order, modify cargo, or acquire/cancel a reservation. Expired pending requests are excluded without pruning the live queue.

The workshop control channel is protocol **3** because the request gained a bounded optional player UUID and the snapshot gained bounded access entries. Client and server need the matching build.

## Verification

The Forge/JUnit suite covers complete snapshot/action round trips, negative coordinates, holder/paused/queue metadata, access entries, bounds and persisted sharing. Standalone reservation checks verify status reads neither prune pending requests nor change active leases.

The real shared-workshop server fixture checks owner/shared/denied access and read-only status around a paused reservation, persists the grant and lease through restart, completes production, revokes the collaborator and requires new work to stop without inventory or lease changes.

The genuine graphical client opens an unclaimed preview before saving and returns to the unsaved target. Later it renders the owned Access page while a paused flour haul holds the mill, with release disabled. After production it renders the page again with release enabled. Status and Access both pass at 640×480. The workflow records render witnesses and screenshots; a new local manual review of this recording was unavailable in the disconnected workspace.
