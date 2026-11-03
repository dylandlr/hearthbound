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

## Completed CI experiment — outcome

The standalone goal-option-memory workflow (run [41689747452](https://github.com/dylandlr/hearthbound/actions/runs/41689747452)) passed. The 3 seed × 6 scenario × 40 held-out simulated-episode matrix produced the following equally weighted flour-success rates:

| Policy | Mean simulated flour success |
|---|---:|
| Frozen goal-bonus neural Q, no scheduler | 67.50% |
| **Frozen same neural Q + explicit goal-option memory** | **83.89%** |
| Scripted reference planner | **83.89%** |

The **16.39 percentage-point** improvement over standalone neural Q was accomplished by explicit engineered scheduling; the option-memory arm **matched the scripted reference exactly in all 18 seed × scenario aggregate cells**. This is strong evidence that a hand-designed coordination layer can rescue this particular simulator workflow, but **not evidence of learned hierarchical planning or neural superiority**. The neural Q-values still break ties among eligible source inspections/hauls; the engineered scheduler supplies much of the decisive logic.

The simulation recorded **170 option resumptions** from secondary work to primary wheat seeking across the 720 evaluated goal-memory episodes. A resumption is an internal option transition, not proof of finished flour production or independent social autonomy; corresponding episode outcomes and event traces are archived. Across both-empty scenarios, the scheduler matched the scripted planner's approximately 50% recovery from stochastic restocking.

### Research decision

Retain all three arms as explicit baselines and **do not promote this scheduling result as learned intelligence**. Next compare the engineered hierarchy with (1) a genuinely trained recurrent/option-termination policy and (2) a model with an explicit goal flag but no manually chosen source or option rules. Maintain the same held-out seeds and original reward accounting. Investigate whether learned memory can approach scripted performance without hardcoding the option transition graph, and whether learned behavior survives longer task sequences and simulated interruptions.
