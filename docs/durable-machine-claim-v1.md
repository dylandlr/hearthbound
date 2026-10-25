# Exclusive machine claim v1

A millstone now has a durable, machine-keyed claim recording one operation ID and one citizen UUID. Unlike citizen-scoped work-order keys, this key is shared by competing citizens: a second attempt with a different operation or owner must fail. Claims are unresolved until an explicit, future recovery/retirement protocol exists. They must **not** be silently expired or reassigned.

The existing Create GameTest prepares the claim before motor activation; both credit award and server-restart verification independently recover it and reject a competing claim. The raw claim intent is included in the evidence artifact. Standalone contracts test exact replay, conflicting claim, retained identity after restart and unchanged ownership.

Important limitations: this does not provide a permanent lease or automatic release, and does not implement Minecraft NPC pathfinding, tick scheduling or crash-time machine reconciliation. The fixture machine key currently includes a random incarnation, so production must use a stable, persisted machine incarnation for repeatable claims across new work orders.
