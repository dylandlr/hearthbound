# Hearthbound v3.7 — Citizen-local state schema

Adds a bounded citizen-owned status sensor independent of research candidate eligibility. It can sample a living villager in a loaded local chunk after its first milling experiment has become ineligible.

Schema v1 (10 features): health fraction; persistent food, shelter, danger, combat, exploration and cooperation instinct priors; known wheat-milling recipe flag; normalized count of personally known recipes; juvenile flag.

Unlike the research proposal sensor, this does not require a wheat source, a millstone, or an available hypothesis. It does not load distant chunks.

**Caveats:** Instincts are fixed seeded priors, not physiological food/shelter inventories and not learned genes. Health is measured from Minecraft entity state. Knowledge comes from the citizen's own technology records. No hunger, relationship, colony priority or general-purpose environmental inventory features have been fabricated. This is a *new schema*, not interchangeable with the existing 11-feature ResearchObservationVector or SavedData replay records. Both original and successor states must use identical schema/version to construct RL transitions.

This change does not yet rewrite the research reward hook to use this sensor and does not create a trained policy. Real Forge compilation and Minecraft behavior tests pending.
