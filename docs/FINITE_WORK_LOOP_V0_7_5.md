# Hearthbound v0.7.5 — Finite autonomous haul-to-study progression

## Root issue
The configured HAUL offer previously remained available after successful
delivery whenever source/destination chunks remained loaded. With HAUL higher
priority than STUDY, Sable would keep selecting hauling and could starve
the study phase indefinitely.

## Implementation
- SableAutoWork persists `haulIssued=true` after HAUL_ASSIGNED. A new
  `auto-work-config` resets this flag; disabling/enabling the routine does not.
- SableWorkChoice now accepts an `allowHaul` flag for the autonomous decision
  path while preserving the existing manual `choose-work` behavior.
- The policy no longer offers STUDY once CitizenTechnologyKnowledge reports
  the milling recipe as known.
- WorkOfferLifecycle is a pure Java offer gate used by SableWorkChoice.
- WorkOfferLifecycleTest covers eight positive/negative availability cases and
  was compiled with `javac --release 17` and run locally on OpenJDK 21:
  **8 checks passed**. The GitHub policy-kernel workflow is also updated.

## Expected exercise
1. Configure source, destination and marked primer via /sable auto-work-config.
2. Set HAUL=1, STUDY=4, enable auto-work.
3. Observe one HAUL_ASSIGNED decision followed by actual cargo delivery.
4. On next eligible decision, HAUL no longer offered and STUDY may be selected.
5. After theoretical learning, STUDY no longer offered.
6. Reconfigure to start a fresh one-haul exercise.

## Limits
This is a *finite test-workflow rule*, not an organic job-board scheduler.
The flag is set at successful **assignment**, not verified delivery. Interrupted
or quarantined hauling still blocks the citizen until manual recovery.
The server-authoritative actual inventory checks and reservation claims remain
inside SableHauling, and Forge gameplay and full project compilation are
unverified. No claim is made that the in-game loop has executed successfully.
