# Source claim test plan

This change connects an in-memory source claim table to Sable hauling, not the durable HaulLedger prototype.

1. Spawn two Sable villagers and assign a wheat transfer from the same chest to both. The second assignment should be rejected while the first is active.
2. Complete the first job, then confirm the source can be assigned again.
3. Pause delivery by filling the output; check the claim remains held.
4. Restart mid-haul and observe that claims are reacquired only opportunistically. Entity-load order can alter ownership.
5. Verify counts before/after shutdown and repeated use.

Known gaps: claims do not release on villager death or abandonment, are not persisted, do not prevent player or hopper mutation, and do not make transfers atomic. Gameplay is not verified. Next: persistent SavedData claims, lifecycle cleanup, and crash reconciliation.
