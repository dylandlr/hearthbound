# First Mill citizen evidence contract v3.6

## Validated physical baseline
GitHub Actions run 38916655778 passed: Sable physically moved a wheat item from an actual Minecraft chest into a powered Create millstone, which produced wheat flour. This was a scripted assignment executed by the Hearthbound hauling actor, **not learned task choice**.

## New implementation
- `MillExperimentTrace.beforeDelivery` checks loaded Create millstone, 1 wheat cargo, and readable item handler, and records job UUID, machine location, baseline flour quantity, and tick in the villager's persistent NBT before insertion.
- `MillExperimentTrace.deliveryComplete` marks the experiment DELIVERED only after the actual Minecraft item handler returned no remainder.
- `/sable mill-trace` compares actual flour currently present to the recorded baseline and yields a **CANDIDATE_WHEAT_TO_FLOUR** observation when the output is higher.
- No automatic learning reward, recipe unlock, or knowledge transfer. If the machine or its inventory is unavailable, the trace remains unconfirmed.

## Important scientific boundary
A before/after item-count difference does not prove the particular millstone processing callback caused the output. Other actors could modify the inventory between observations. For real technology discovery, hook a trusted Create processing completion path with input/output recipe identifiers and world tick, bind a unique work-item token or enforce exclusivity, and persist deduplicated event receipts before awarding knowledge. Multiple independent trials can strengthen confidence but do not replace causal attribution.

## Acceptance test
`scripts/rcon_sable_first_mill.py` now requires a job-specific trace after Sable completes the real hauling task and the real millstone produces flour; expects phase DELIVERED and candidate verdict, and expressly NO_RESEARCH_CREDIT.

The v3.6 CI run must pass before this is considered verified in Minecraft.
