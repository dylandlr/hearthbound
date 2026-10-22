# Hearthbound v3.3 — Create millstone implementation inspection

Authoritative source inspected: https://github.com/Creators-of-Create/Create/blob/mc1.20.1-6.0.8/src/main/java/com/simibubi/create/content/kinetics/millstone/MillstoneBlockEntity.java

The pinned Create source exposes `MillstoneBlockEntity.inputInv` (1 slot), `outputInv` (9 slots), public `timer`, `getSpeed()` and `getProcessingSpeed()`. The server-side `tick()` decreases the timer by processing speed and invokes a private `process()` after the timer crosses zero.

In `process()`:
1. The current `lastRecipe` is validated or reselected against input.
2. `inputInv.getStackInSlot(0)` is read; one item is consumed via `shrink(1)` and `inputInv.setStackInSlot(...)`.
3. `lastRecipe.rollResults()` chooses the actual produced item stacks (potentially stochastic).
4. Outputs and crafting remainders are inserted into `outputInv`.
5. The machine marks itself changed.

**Consequences**:
- We can inspect actual timer, RPM, input and output machine fields directly, rather than guessing which items are exposed through the generic Forge ITEM_HANDLER.
- We must instrument the precise `process()` mutation window to establish which input was consumed and which outputs were actually inserted. An end-tick delta is only a debug trace; concurrent extraction could make it incomplete.
- A future injection/wrapper needs to capture actual output insertion amounts and RNG results without calling `rollResults()` again.
- The source has no public per-operation completion event that our code currently uses. Any Mixin/injection requires compile, mutation correctness, and restart GameTests.
- In the absence of a valid recipe, processing may terminate without producing outputs; this cannot award a discovery.
- Recipe and server machine internals are **not** automatically agent observations: respect partial observability and reveal only acquired knowledge.

**Implemented in this commit:** Diagnostic inspection and tick trace now read Create's concrete `MillstoneBlockEntity` internal fields.
**Still unverified:** compilation of these source changes, live Forge/Create startup, receipt hook, citizen learning.

The dedicated server smoke test remains EULA gated. No acceptance has been inferred or performed.
