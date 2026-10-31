# Citizen inventory ownership v0

A pure-Java citizen-scoped inventory snapshot and one-wheat reservation policy now exist. The caller must supply the same authorized citizen UUID as the inventory owner. Missing wheat, foreign ownership and bulk reservations are rejected. The source state is immutable and the unit contracts check conservation and fail-closed behavior.

This is a **contract only**, not a Minecraft NPC inventory component or durable world state. The real Create adapter continues receiving an ordinary server-owned ItemStack from the GameTest. A subsequent world adapter must persist the citizen inventory, atomically reconcile the source debit with the millstone insertion across server crashes and bind authorization to the durable citizen work assignment; the current snapshot cannot provide those guarantees.

Acceptance of this increment is standalone Java contracts and the Forge compilation job. The tagged Minecraft experiment continues to test the earlier server-side ItemStack transfer; do not claim that this new inventory model is exercised end-to-end in game.
