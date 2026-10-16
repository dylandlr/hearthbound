# First Mill v4.9 — audited release and reuse regression

At `48cf294f`, all four First Mill GitHub Action jobs succeeded.

## New coverage
The Sable dedicated-server gameplay test now exercises the completed-job lease lifecycle:
1. Demonstrates that a direct Create `process()` receipt and matching lease exist.
2. Rejects a release while actual mill flour remains.
3. Demonstrates another citizen's conflicting lease is refused and a separate unpicked reservation can be cancelled.
4. **Test fixture only:** uses the Minecraft administrator's `/data modify block` to clear `OutputInventory.Items`. This does not simulate a player or citizen physically collecting output and should never be part of production gameplay.
5. Verifies the mill has zero flour in inventory, rejects a mismatched job UUID, then performs a successful `/sable mill-release` using the original job.
6. Verifies the old reservation is removed, a repeated release is refused, and another citizen can receive a new haul job with a fresh lease on the released mill.
7. Separately maintains the existing save/stop/restart test without releasing its original lease.

## Production considerations
The actual production release command still requires the original job and citizen, a cargo-free completed delivery, a direct Create processing receipt, the loaded Create millstone, and empty input and output inventories. It writes a persistent replay tombstone. A physical output collection mechanism is the next necessary integration. External Create belts, vanilla hoppers and player inventory mutation remain outside Hearthbound's reservation policy; therefore **no research rewards or recipe unlocks** are issued.

The new release/reuse checks are **committed but not claimed to pass** until their updated CI run completes.
