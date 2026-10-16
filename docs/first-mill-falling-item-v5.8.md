# First Mill v5.8 — falling-item bypass fix

## Regression that prompted this change
The v5.7 Minecraft gameplay run `38969953760` **failed**. Real dropped wheat physically entered the powered, reserved millstone despite passing Forge IItemHandler and Create direct-belt API negative controls. Three other CI workflows passed. This was a genuine missing ingress path, not a false test failure.

## Root-cause investigation
Create 6.0.x `MillstoneBlock.updateEntityAfterFallOn(BlockGetter, Entity)` explicitly processes falling `ItemEntity` and invokes the millstone's capability-based inventory insertion. This is a distinct physical world interaction requiring an explicit server-side gate; previous tests of the capability and direct-belt routes did not guarantee that the whole item-entity collision path was protected.

## New safeguard and acceptance criteria
A Create `MillstoneBlock` HEAD Mixin vetoes `updateEntityAfterFallOn` for physical `ItemEntity` entities landing at or immediately above a **reserved** Hearthbound millstone. It leaves the world entity and item stack untouched, but does not change the behavior of unreserved Create mills.

The dedicated-server RCON gameplay regression summons a tagged wheat item above the powered reserved mill, checks that its physical inventory remains wheat-free over several observations, and requires the tagged item to remain in-world. The injection logs `HEARTHBOUND_FALLING_ITEM_DENIED`. The gameplay workflow must now find that specific interception marker if the RCON test passes.

## Explicit limits
This covers one missing physical falling-item route. Real moving conveyors, arbitrary player/mod direct `inputInv` updates, and direct NBT edits remain unprotected or incompletely tested. The signed identity of otherwise indistinguishable wheat stacks is not yet established. No AI learning credit, recipe unlock, teaching reward or Outcome Ledger update is allowed.

Only call the v5.8 guard verified once the new CI run is green.
