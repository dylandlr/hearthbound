# Hearthbound v0.6: Knowledge, institutions and autonomous learning

## Approved boundary contracts

**Simulation authority.** The Minecraft server owns physics, entity state, inventories,
claims, permissions and verified outcomes. Policies cannot mutate world state.

**Partially observed citizen cognition.** A policy reads only an agent-specific snapshot:
needs, personality, perceived opportunities, known recipes, relationships, resources
and allowable hierarchical actions. Observations are schema-versioned.

**Belief versus skill.** An agent has exposure, belief, theoretical understanding,
practical competence, evidence, and provenance. A book improves theory, not
practical mastery. A physical Create recipe completion is objective evidence,
not automatically a universal unlock.

**Evidence.** World journal entries identify event, source, location, tick,
item delta and causal candidate. Physical verification must be deduplicated.
Provenance confidence and causality must not be conflated.

**Learning modalities.** INNOVATE discovers/test hypotheses; OBSERVE_BOOK reads
authenticated content; OBSERVE_CITIZEN learns from a demonstrator; EXPLOIT uses
existing know-how to produce; REST maintains survival.

**Reward channels.** Personal, colony and research are independent. Cooperative
credit is allocated only by verified contribution, with replay protection.

**Institution model.** Libraries are authoritative inventories of accessible
knowledge objects plus spatial access rules and institutional policies. A study
job is a hierarchical action with travel, observe, practice and completion phases.

**Baselines.** Scripted rules first; same fixed observation schema to MLP.
Later compare tree/random forest and RL in deterministic fast simulation.
LLMs remain deferred.

## Implementation added
LearningDecisionPolicy v1 is a deterministic candidate-action baseline with
partial observations, legal-action gating and explicit score rationales.
The unit tests cover needs, access masking, competence and schema rejection.
This is not trained learning and not yet connected to the citizen event loop.

## Critical repairs before true autonomy
1. Replace current constant citizen literacy (60) with persisted literacy/traits.
2. Replace placeholder written-book grants with authenticated book/lesson mapping.
3. Separate information exposure from confirmed competence in persistent records.
4. Introduce a single task scheduler arbitrating hauling, study, survival and
   social duties. Avoid free-running NPC scripts competing on movement.
5. Track study sessions across save/restart with replay-safe completion evidence.
6. Add actual game tests for book removal, interruption, pathfinding and restart.
7. Add evaluation runs contrasting isolated, library-only, social, and mixed groups.

## Research basis and limits
Wellman, Tuyls and Greenwald (2025): simulator-derived empirical games to compare
strategies; Sandholm (2015): hierarchical/information abstractions can distort
strategic outcomes; Krause and Golovin: diminishing returns for appropriate
submodular coverage objectives; Chan et al. (2024): provenance and monitoring.
These papers do NOT establish optimal reward coefficients or validate this
Minecraft implementation. Record all weights as experimental hypotheses.
