# First Mill v5.4 — Forge item-handler ingress authorization

## Green baseline
Commit `c56c5b28` passed all four real-Minecraft CI workflows: Create integration, normal powered milling, Sable hauling and tamper controls, and restart persistence.

## Implementation
- `MillTransferGate` supplies a short-lived, thread-local, matching job/citizen/millstone authorization for Sable's specific inventory operations.
- A new Mixin guards Create's internal `MillstoneInventoryHandler.insertItem` entry. On reserved research mills, a Forge item-handler insertion without Sable's currently matching authorization is returned unchanged (rejected). Unreserved mills are not altered.
- Sable's simulation/preflight and actual one-wheat delivery use separate matching authorization scopes, with mandatory `finally` cleanup; no permission is retained between calls or through save/restart.
- An admin-only `/sable mill-probe-external-insert x y z` negative control attempts one real wheat insertion through Create's Forge item-handler *without* that authorization. It must report `EXTERNAL_INSERT DENIED` and leave the physical inventory unchanged.
- The existing Create direct-process veto, live monitor, persisted taints, evidence restart, and normal machine processing remain in place.

## Remaining risk / scope
This guards one concrete insertion route: Create's public Forge `IItemHandler` implementation. It does **not** yet intercept belt-direct handling, an external mod holding direct `inputInv` access, direct NBT/data edits, or all vanilla/player interaction routes. It does not prevent indistinguishable substitution through such routes and cannot be treated as tamperproof physical provenance. Never issue experimental knowledge, reward, teaching credit or Outcome Ledger allocations from this partial layer.

The v5.4 real-server regression must pass before describing this internal Create Mixin and authorized Sable delivery as verified. If the internal class Mixin fails during Forge startup or compilation, fix the target/outer-instance linkage rather than weakening the mandatory denial check.
