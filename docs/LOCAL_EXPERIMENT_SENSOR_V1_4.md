# Hearthbound v1.4 — Local physical experiment observation

This slice binds the v1.3 deterministic experiment-selection policy to **real loaded Minecraft state**, without using the global recipe registry to discover recipes.

A new `LocalMillExperimentSensor.consider` requires:
- A Hearthbound citizen in the same ServerLevel;
- A loaded source inventory with wheat accessible to the existing hauling observation;
- A loaded `create:millstone` identified via Minecraft's registered block ID;
- Both positions within eight blocks of the citizen;
- No prior proposed/confirmed/falsified hypothesis for this recipe.

The available hypothesis currently comes from one explicit candidate template (wheat -> flour). Citizen curiosity is drawn from their existing varied instinct profile. Fatigue and scarcity remain neutral policy inputs rather than fabricated physiological metrics.

The admin-only `sable experiment-local <source> <mill>` command accepts physically observed locations, invokes the deterministic policy and only writes a **PROPOSED** record if the policy selects the candidate. No materials move, no research credit is minted, and no recipe is unlocked by proposal. Existing hauling, exclusive reservation and actual Create process receipt remain the physical execution and confirmation path.

The First Mill acceptance script rejects an irrelevant block as a possible machine and then proposes using a real Create millstone; the existing event-based callback must still confirm the hypothesis.

**Not done:** General candidate discovery, autonomously selected coordinates, citizens undertaking the full experiment, real fatigue, and trained deep-learning agents. This is a bounded live-world sensor, not fully emergent discovery.
