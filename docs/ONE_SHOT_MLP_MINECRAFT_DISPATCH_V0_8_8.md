# v0.8.8 — First model-selected one-shot Minecraft task

The new admin-only `/hearthbound policy_trial <source> <mill> TRAINED_MLP` command:
1. Reads authoritative loaded Minecraft source and destination state.
2. Requires an actual Create millstone with nonzero kinetic speed and no inputs or outputs.
3. Requires a real wheat item in the source's inventory and exactly one nearby marked Sable villager with no active job.
4. Evaluates bundled, checksum-verified 5→12→4 MLP, applies high-level action masking, and requires `REQUEST_WHEAT_HAUL`.
5. Delegates *once* to existing `SableHauling.assign`, which controls source claims and mill reservations, then lets the existing server-side movement/inventory integration perform all physical work.

The real dedicated-server test replaces the manual citizen mill haul assignment with this MLP-selected task and retains flour output, Sable memory, and post-restart memory checks. All other player and third-party Create machinery behavior is unchanged.

## What a passing test proves

A trained neural model's recommended high-level action caused an authorized real task assignment and a genuine Minecraft work outcome. It does *not* establish autonomous long-running decision loops, learning from Sable's previous experience, comparative performance advantage, RL, or production-grade crash consistency.

The MLP is **imitation trained** from scripted rules; in this specific empty-mill case it selects the same action as scripted. Reproduction requires a full Forge/Create server CI pass and authoritative logs `REAL_MLP_SELECTED_SABLE_HAUL`, `REAL_CITIZEN_EXPERIENCE_OBSERVED` and persisted restart counter.

## Deliberate safeguards

- Operator-admin command required: no independent background task scheduling.
- Only REQUEST_WHEAT_HAUL can mutate the world, through SableHauling.assign.
- No direct neural access to movement, inventory mutation, research reward, or console commands.
- Fail closed when world, citizen, source, machinery, model or task state is invalid.
- No replay of active tasks; existing task ownership and reservation checks remain authoritative.
- Destination output handling is not yet an MLP-executed action.

## Next controlled comparison

Run scripted and trained MLP in **independent cloned Minecraft worlds** with matching initial inventories, seeds, machine power, citizen traits, task layouts, and observation budgets; record task completion, elapsed Minecraft ticks, inventory transitions, wasted actions, and safety faults. Repeat with randomized held-out layouts and multiple seeds before claiming any superiority. Add a genuine reward-driven training environment before claiming reinforcement learning.
