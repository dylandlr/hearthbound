# Hearthbound v0.10.3 — Hierarchical goal continuity experiment

## Rationale

v0.10.1's reward-trained neural Q citizens often completed secondary work without successfully returning to flour production. In v0.10.2, adding a +1 flour-goal training bonus raised overall simulated flour success from 53.89% to 67.50%, but still lagged the scripted reference's 83.89%. A scalar reward change alone did not reliably solve long-horizon task management.

## New architecture — explicit goal memory, not a recurrent neural network

A per-episode `GoalMemory` record retains the original goal `PRODUCE_FLOUR`, current option, whether secondary work started or completed, and transitions back toward the primary objective.

The hand-designed option scheduler has four states: `SEEK_WHEAT`, `SECONDARY_ONCE`, `WAIT_RECHECK`, and `DONE`. It uses **only observed resource flags and confirmed task events**, not hidden world resource amounts. It requests hauling only from actually observed available sources; it can do one secondary job when both sources are known empty, then explicitly resume the flour objective on the `OTHER_TASK_COMPLETE` event. It waits/rechecks rather than repeatedly executing already-completed secondary tasks. The underlying Q model is still used to select among eligible inspection or hauling candidates.

This is a **scripted hierarchy over frozen learned Q-values**, NOT a learned hierarchical policy, recurrent network, Minecraft deployment, social memory or evidence of spontaneous goal formation.

## Controlled evaluation

The base network is exactly the v0.10.2 `goal_bonus` training variant (same seeds 11/13/17, 350 simulator episodes); it is evaluated without updates. Three policy arms share the same initial held-out world seeds in six scenarios (40 worlds per training seed/scenario): (1) frozen neural-Q without option memory, (2) same frozen neural-Q with explicit goal memory, (3) original scripted task planner.

All evaluation arms use the original simulator transitions and personal/colony rewards. The output logs action counts, actual simulated flour success, secondary task completions, alternate hauling, timeouts, invalid requests, option transition receipts and a full decision/event sequence for one held-out example per scenario. Checkpoint hashes are validated unchanged.

This is a **720-episode evaluation per policy**, not a new Minecraft run, and no new neural weights are learned for the hierarchy.

## Engineering acceptance

- A complete secondary-job lifecycle explicitly returns to the primary goal only after task completion event.
- No inventory is read through hidden simulator state to choose an action.
- Known empty/unknown/stale sources cannot authorize hauling.
- Existing frozen neural baseline flour outcomes and unchanged colony rewards match the prior evaluator.
- No masked task actions, no real Minecraft dispatch and no claims of trained recurrent memory.
- Compare failures and timeouts, not just successful trajectory excerpts.

## Next research phase

Inspect whether goal memory closes the gap against the scripted reference. If option scheduling still underperforms, introduce learned option termination and train a small recurrent state model or explicit task-conditioned policy on temporally split data. Multiple citizens, real pathfinding, job contention, persistence and Create interactions remain future Minecraft integration gates. Fresh Forge CI still depends on resolving upstream Maven TLS issues.
