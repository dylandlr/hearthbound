# Shared workshops

A millstone has one persistent owner and up to eight explicit collaborators in its dimension. Starting an order through the native screen claims an unowned mill for the assigning player. The owner can open **Status → Access**, select another online player and press **Share**. Existing collaborators, including offline ones, can be selected and revoked. Server operators can repair access without silently replacing the owner.

A collaborator can assign their own workers to the mill. Each work order records the manager whose permission authorized it. Revoking that player does not erase an active haul, cargo or reservation; the current transfer finishes, then the scheduler reports `WORKSHOP_ACCESS_DENIED` before taking more stock. Restoring access and saving the order authorizes scheduling again.

Ownership and collaborator UUIDs persist in dimension-scoped SavedData. Names shown in the screen come from connected server players; an offline collaborator uses a generic label. Client requests contain a server-authored UUID selected from the status snapshot. Adding access requires that player to be online. The server rechecks the authenticated worker session, revision, build permission, loaded millstone, 32-block range, owner/operator authority and the eight-member cap.

Each hauling job reserves both its source and destination before assignment. A failed request takes neither endpoint and creates no haul or cargo. Conflicting workers report **Waiting for a shared station** and return to their waiting spots. Requests keep their queue position while retrying; earlier overlapping requests have priority, while unrelated stations can operate independently.

The reservation stays with the worker UUID and exact job ID through pickup, travel, delivery, pauses and stopped orders. It is released only when that haul finishes, the loaded worker no longer has that job, or the worker is destroyed/discarded. Chunk unloads and graceful server shutdown preserve it. Saved reservations load before new jobs can acquire endpoints. An unloaded holder is never treated as expired, and no holder chunk is forced to load.

An ungranted waiting request can expire after 120 server ticks without retrying; it owns no stock or cargo. The queue is rebuilt after restart. Active reservations have no expiry. A job moved to another dimension waits until it returns to its original dimension.

## Ownership and recovery

- **Status → Access → Release ownership** clears the owner and collaborator list only when the mill has no active reservation.
- The release button stays disabled while either leg of a haul reserves the mill.
- `/hearthbound workshop_status <mill x y z>` shows the owner and active reservation.
- `/hearthbound workshop_release <mill x y z>` is an operator recovery command with the same reservation guard.
- Stop order preserves the current haul, reservation and mill ownership. Resume haul retries that same job.
- Releasing ownership causes existing orders to stop scheduling until an authorized player explicitly saves/starts them against the newly claimed mill.

Ownership applies to the millstone coordinate, including a replacement at that coordinate. Barrels remain shared stockpiles. This coordinates colony controllers; it does not prevent player inventory access, third-party automation or interactions governed by land-claim mods.

The first implementation reserves both endpoints for the whole haul. It favors consistent scheduling over maximum parallel throughput. It does not add death-item recovery or make entity, inventory and SavedData writes crash-atomic.

## Acceptance coverage

The Forge/JUnit suite checks the eight-player cap, owner/operator management, collaborator use, revoke, release, dimension separation, bounded packets and owner/share/lease NBT round trips.

The actual Forge + Create fixture grants a second supervisor access, configures two workers against one powered mill and shared stockpiles, and rejects a stranger without changing their worker. It verifies failed acquisition leaves the other endpoint free and discarding an empty worker releases its reservation. The first worker physically picks up four wheat; the fixture stops its order and pauses the haul while the second worker waits.

After a real save and complete server restart, the fixture requires the owner, collaborator grant, four wheat of cargo and exact reservation read from disk. Ownership release remains blocked. Resuming finishes the delivery; the second worker produces and stores two flour. The fixture then revokes the collaborator, raises the target and requires `WORKSHOP_ACCESS_DENIED` with source 4, flour 2, cargo 0 and no leases. A later check verifies no replay.

The genuine graphical client renders the owner-only Access page. A paused reservation produces `release=false`; the same mill after completion produces `release=true`. Both the Status and Access layouts pass at 640×480. The single-client graphical fixture has no second connected player, so the actual grant/revoke lifecycle is covered by the real dedicated Create server and registry tests rather than a two-player click-through.
