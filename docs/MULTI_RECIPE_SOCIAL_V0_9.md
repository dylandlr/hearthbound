# Multi-recipe social learning v0.9

The existing knowledge ledger was recipe-agnostic but the autonomous citizen loops were hardcoded to wheat milling. This slice lets teachers advertise personally known recipe IDs and lets nearby learners request any offered unknown recipe.

- `CitizenTechnologyKnowledge.entries`: immutable personal knowledge snapshot.
- `TechnologyOffers.advertisedBy`: opt-in teacher offer of personally learned recipes with confidence >= 0.15.
- Teachers pick among nearby, line-of-sight students and offered recipes, prioritizing a student's explicit request, then distance and recipe ID for deterministic tie breaking.
- Learners observe only physically visible teachers' advertised recipe IDs, and request the first unknown one using their existing student initiative policy.
- The original wheat milling acceptance test remains, now as a special case of general social recipe propagation.

This DOES NOT create new verified manufacturing/experiment hooks. Currently wheat milling remains the physically verified first recipe; other knowledge must originate from an existing valid `discover`, `study` or `teach` path. Nor is this an actual generalized emergent invention algorithm or trained neural policy.

Next: test two distinct recipes, seed teacher knowledge only through a valid provenance path, ensure unknown and unavailable recipes never propagate, then bind recipe discovery to independently verified Create machine transactions and compare deterministic policies with MLP/RL agents. 
