# First Mill v3.7: observed Create processing cycle

The Create 6.0.8 runtime test on commit `af266828` already passed real server Sable hauling and flour production. A separate v3.6 candidate evidence trace was added later; its verification is tracked by GitHub Actions.

## Stronger observation implemented
- `MillExperimentTrace` records the hauling job's UUID, millstone location, baseline flour and real insertion result.
- After delivery, the Sable server tick inspects the **actual** `MillstoneBlockEntity`, using Create's `inputInv`, `outputInv`, `timer` and `getSpeed()`.
- The per-citizen NBT trace becomes `PROCESSING_OBSERVED` only when wheat is in the machine while it is rotating with an active recipe timer.
- Later, the trace becomes `CYCLE_OUTPUT_OBSERVED` only if the input is gone and flour increased from the pre-delivery baseline. It records ordered processing/output ticks.
- The Minecraft RCON end-to-end test requires processingTick < outputTick and **NO_RESEARCH_CREDIT**.

This is a **sampled machine-state transition**, not Create's private `process()` callback. Because other machines/actors might mutate input/output inventories, observation alone does not provide unambiguous causal attribution. No recipe is unlocked, no research or reward is issued, and the learning agent still uses the scripted hauling task. A trusted per-process callback (or exclusive experiment reservation plus independently verifiable output event), persistence and replay protection are still required before knowledge credit.

Source examined for design: `Creators-of-Create/Create` `mc1.20.1/dev` `content/kinetics/millstone/MillstoneBlockEntity.java`. The Create version used in Hearthbound is pinned to 6.0.8.
