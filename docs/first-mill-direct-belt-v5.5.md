# First Mill v5.5 — Create direct-belt ingress guard

## Verified baseline
Commit `123b8633` passed all four dedicated Minecraft server workflows: normal Create integration, powered milling, Sable's physical hauling and Forge item-handler ingress negative control, and saved-world evidence restart.

## New protection
The server now intercepts `DirectBeltInputBehaviour.handleInsertion(TransportedItemStack, Direction, boolean)` via a Sponge Mixin. This is Create's documented direct-belt insertion method, including its normal default callback into item-handler inventory access. For a **reserved Create millstone**, the call immediately returns the original transported stack unchanged, so a belt transfer cannot place wheat into that experimental machine. Calls targeting any **other Create machine** or an **unreserved millstone** are left untouched.

The administrator regression command `/sable mill-probe-belt-insert x y z` exercises this Create behavior directly on a held millstone. The end-to-end gameplay CI checks `BELT_INSERT DENIED` alongside the Forge `EXTERNAL_INSERT DENIED` check, and continues to verify that normal Sable wheat insertion is permitted.

## Important boundaries
This directly tests the behavior's insertion method, rather than constructing a moving physical belt assembly. We must eventually verify the full moving-belt transport path, belt redirects, hoppers and other mod interoperability in an actual gameplay test world. Direct `inputInv` mutation and NBT remain possible bypasses. Thus this is a scoped protection for Create's direct-belt API, not comprehensive item provenance or multiplayer tamperproofness. No autonomous recipe discovery or learning rewards are enabled.

CI for the new Mixin must pass before treating the belt guard as verified.
