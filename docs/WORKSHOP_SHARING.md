# Shared workshops

A millstone now has a persistent owner in its dimension. Starting an order through the screen claims an unowned mill for the assigning player. Workers managed by that player can share it. A different player's assignment is rejected before changing the worker or taking stock. Operators can authorize an order without changing an existing mill's owner. Console-created workshops belong to the server; legacy orders adopt their saved supervisor, or server ownership when none exists.

Each hauling job reserves both its source and destination before assignment. This covers wheat supply, flour collection and manual operator hauling. A failed request takes neither endpoint and creates no haul or cargo. Conflicting workers report **Waiting for a shared station** and return to their waiting spots. Requests keep their queue position while retrying; earlier overlapping requests have priority, while unrelated stations can operate independently.

The reservation stays with the worker UUID and exact job ID through pickup, travel, delivery, pauses and stopped orders. It is released only when that haul finishes, the loaded worker no longer has that job, or the worker is destroyed/discarded. Chunk unloads and graceful server shutdown preserve it. Saved reservations are loaded before new jobs can acquire the endpoints. An unloaded holder is never treated as an expired job, and no holder chunk is forced to load.

An ungranted waiting request can expire after 120 server ticks without retrying; it owns no stock or cargo. The queue is rebuilt after restart. Active reservations have no expiry. A job moved to another dimension waits until it returns to its original dimension.

The native editor now exposes this information through its read-only **Status** page. See [workshop status](WORKSHOP_STATUS.md) for selected-station previews, ownership/access, holders and waiting counts.

## Ownership and recovery

- `/hearthbound workshop_status <mill x y z>` shows the owner and active reservation.
- `/hearthbound workshop_release <mill x y z>` is operator-only and releases ownership only when the mill has no active reservation. It never clears a carrying worker's lock.
- Stop order preserves the current haul, reservation and mill ownership. Resume haul retries that same job.
- After ownership is released or changed, existing orders need a matching workshop owner before scheduling again. An explicit Save/Start performs the ownership check again.

Ownership applies to the millstone coordinate, including a replacement at that coordinate. Barrels remain shared stockpiles. This is colony-controller coordination; it does not prevent player inventory access, third-party automation or interactions governed by land-claim mods. Player-to-player sharing permissions and ownership controls inside the screen are follow-up work.

The first implementation deliberately reserves both endpoints for the whole haul. It favors consistent scheduling over maximum parallel throughput. It does not add death-item recovery or make entity, inventory and SavedData writes crash-atomic.

## Acceptance coverage

The standalone reservation suite exercises atomic acquisition, overlapping queue priority, independent resources, safe request expiry, exact-job release and restoring active locks. JUnit also checks owner/operator access, dimension separation and owner/lease NBT round trips.

The actual Forge + Create fixture starts two independently configured workers on one powered mill and shared stockpiles. It rejects another owner's assignment without changing the worker, verifies failed acquisition leaves the other endpoint free, and checks that discarding an empty worker releases its reservation. The first worker physically picks up four wheat; the fixture then stops its order and pauses the haul. The second worker retries without extracting more stock.

After a real save and complete server restart, the fixture requires the owner, four wheat of cargo and the exact reservation read from disk. It checks ownership cannot be released while that haul is reserved. Resuming the first worker finishes the delivery; the second worker produces and stores two flour, reaches its target and leaves both workers without active cargo or leases. A later check verifies no replay. Resources and creative-motor power are staged; neither production worker is teleported.

The original dedicated-server restart test now also requires its station reservation to have been loaded from disk. Existing Create production, waiting/navigation, worker selection and native-screen graphical acceptance remain regression gates.

The fixtures explicitly provide a ticking chunk margin for return paths and wait for saved entity sections after server readiness. The graphical observer retries genuine right-clicks while following a moving worker. These are readiness/interaction measures; all cargo, owner, exact-job and stock assertions remain required.
