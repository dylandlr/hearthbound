# Emergent Technology Runtime v0.5

## Milestone

The First Mill research path now crosses the real Minecraft/Create runtime boundary.

A successful reserved wheat-milling experiment must satisfy this chain:

1. a Hearthbound citizen physically delivers exactly one authorized wheat item;
2. Create's real `MillstoneBlockEntity.process()` callback observes input consumption and flour production;
3. `MillProcessReceipts` records a unique server-side receipt;
4. that same verified receipt grants the three-domain research reward through `MillResearchRewards`;
5. the experimenting citizen gains `create:milling/wheat` as `DIRECT_EXPERIMENT` knowledge;
6. the citizen may teach the recipe to a nearby Hearthbound citizen, producing `TAUGHT` knowledge that retains the original evidence provenance.

Candidate polling observations still remain `NO_RESEARCH_CREDIT`. Only the point-of-execution Create callback can trigger the automatic award.

## New runtime inspection

- `sable mill-reward <jobId>` shows the persisted research award.
- `sable tech-inspect` shows the selected citizen's recipe knowledge and provenance.
- `sable teach-nearest "<recipeId>"` performs an explicit local teaching action to the nearest Hearthbound citizen within four blocks.

Teaching is not a global tech-tree unlock. The teacher must already know the recipe; the student receives reduced confidence and keeps the original evidence ID plus teacher UUID.

## Acceptance test

`scripts/rcon_sable_first_mill.py` now requires:

- real powered Create milling;
- a direct callback receipt;
- automatic persisted research reward;
- direct experimental knowledge on Sable;
- local teaching to Iven;
- retained `TAUGHT` knowledge on Iven;
- all existing contamination, replay, reservation, and taint negative controls.

This closes the first vertical slice of the emergent technology tree: physical experiment -> causal reward -> personal knowledge -> social transmission.

## Next

The next slice should replace the admin-invoked teaching command with a policy-selectable social action using partial observations, relationship state, personality/traits, and communication opportunity. After that, knowledge should be consumable by hierarchical task selection so recipes are actionable only when the acting citizen actually knows them.
