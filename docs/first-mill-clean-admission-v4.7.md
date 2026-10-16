# First Mill v4.7 — clean-machine experiment admission

## Baseline
The most recent pre-change commit `98cfca61` passed all four Minecraft workflows, including two-citizen reservation denial, audited completed-job release, replay rejection, fresh job reuse, direct Create processing receipt and restart recovery.

## New guard
A **new** Create millstone reservation is now refused unless Create's actual `MillstoneBlockEntity.inputInv` and `outputInv` are completely empty. The check happens on the server before Hearthbound installs the reservation or assigns a job. Existing matching reservations are unaffected. A failed acquisition releases the attempted source chest claim.

## Negative control
In the Sable gameplay RCON test, after the old reservation has been audited and released:
1. Inject one flour into the physical millstone output as a test fixture.
2. Confirm the mill inspector sees nonzero flour.
3. Attempt to assign a new citizen's wheat-hauling experiment to the unreserved but contaminated millstone.
4. Require rejection and confirm the machine is still unreserved.
5. Clear the flour and require that a fresh job can acquire the millstone.

## Limitations
This is **admission hygiene**, not an immutable lock on the physical inventory. Players, hoppers, belts and other mods can still mutate the machine after admission. A shared-world research-credit award remains forbidden. The test's direct NBT insertion is an adversarial test-fixture operation, not a gameplay item-collection mechanic. Full inventory access controls, cancellation after partial progress and stronger causal provenance are still required.

All new checks require updated CI success before being called verified.
