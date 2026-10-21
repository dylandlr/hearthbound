# Hearthbound v3.3 — Versioned partial research observation vectors

Adds immutable, deterministic, 11-wide `ResearchObservationVector` schema v1 built solely from `ExperimentSelectionPolicy.Observation`. This is a **pure encoding primitive**, not yet a trained or deployed MLP.

## Ordered features
0 curiosity; 1 scarcity; 2 fatigue; 3 candidate_present; 4 novelty; 5 material_cost; 6 material_visible; 7 machine_visible; 8 previously_falsified; 9 candidate_count_normalized; 10 eligible_count_normalized.

Each feature is in [0,1]. Candidate features default to zero only with `candidate_present=0`, avoiding interpreting absent candidates as real zero novelty. Candidate order is lexicographically deterministic by recipe ID. Local counts are capped after division by 16; the candidate list itself comes from the bounded local sensor.

## Known limitations

- Scarcity and fatigue in today's physical milling sensor are fixed stub values, not measured citizen physiology. They must not be interpreted as real survival statistics.
- No hunger, energy, fear, society, memory, or actual genetics is encoded because authoritative local sensors for those features are not available here yet.
- No action mask, full recipe embedding, successor observation, durable vector persistence or neural network policy has been integrated.
- This records local experiment candidate information, not omniscient tech-tree availability.
- Once a real Minecraft observation and successor observation are bound to a job, this stable schema can become part of training data. Schema migrations must be explicit.
- Unit tests cover deterministic ordering, missing candidates, normalization and defensive copying. Forge CI remains unverified.
