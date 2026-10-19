# Hearthbound v1.6 — Opt-in citizen research jobs

Introduces `AutonomousMillResearch` as a bounded server-side task:
SURVEY -> POLICY SELECT -> HAUL ASSIGNMENT -> PERSIST HYPOTHESIS -> await trusted Create processing callback.

Enable with `sable auto-research-on`; disable with `sable auto-research-off`. This is opt-in, and considers research at most every 200 ticks. It only selects locally discovered wheat and registered millstone positions. It uses the existing `SableHauling.assign` admission path, including machine reservations, rather than mutating inventories or manufacturing a physical event. A hypothesis is proposed only after a haul assignment is accepted.

## Scope and limitations

The candidate template is still wheat to flour; spontaneous recipe synthesis, physics-driven alternate hypotheses and a trained research policy are not implemented. A post-assignment persistence failure would require an explicit job cancel/reconciliation mechanism; this version assumes the validated template can be stored. Existing job priority arbitration is not yet shared with research jobs, so keep this feature disabled while auto-work is active until a common arbiter is implemented.

## Verification

CI compiles and runs existing Forge checks; the v1.5 parent compile and JAR passed, but its dedicated-server smoke was red because initial RCON haul setup returned empty output. This is not evidence of an autonomous research loop passing. A dedicated acceptance scenario must separately demonstrate a citizen beginning from an available chest and powered Create millstone, claiming a job, hauling wheat and acquiring a confirmed hypothesis from a real Create processing receipt.

## Next

Add research job ownership arbitration and an actual automated First Mill end-to-end script with restart persistence check. Only then promote opt-in autonomous research to a supported gameplay behavior.
