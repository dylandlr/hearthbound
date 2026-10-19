# Hearthbound v1.7 — Exclusive research task admission

This increment closes a live task collision in the opt-in research scheduler.

Before proposing a physical milling experiment, `AutonomousMillResearch.tick` now:
- declines admission whenever the existing auto-work scheduler is enabled;
- calls the persisted `CitizenWorkOwnership.assertFree` reconciliation gate, which checks active hauling, active library movement and study, and conflicting persisted work ownership;
- only after the existing hauling executor accepts the physical job does it verify the HAUL work owner and persist a PROPOSED hypothesis.

The existing `SableHauling.assign` remains authoritative for claims, reservations and physical hauling. Any previously accepted research haul is still interpreted by the trusted Create processing receipt callback, never a synthetic event. This is a conservative exclusive-work gate, not a complete global task priority system.

## Known outstanding limitations

- Task ownership represents a research transport as HAUL rather than a first-class EXPERIMENT lease; future work should introduce a research parent task with nested hauling, using deterministic idempotent transitions.
- A failed hypothesis persistence step after accepted hauling needs an explicit rollback/reconciliation path.
- Dedicated automated autonomous-research E2E has not yet been established; existing server smoke is broader than the research integration scripts.
- The v1.6 base checks had not all finished when this branch was started. The historical v1.5 server smoke failure occurred during the initial RCON hauling setup, before research validation.
- The software still has one concrete research experiment: wheat into a Create millstone. No LLM or trainable policy is used.
