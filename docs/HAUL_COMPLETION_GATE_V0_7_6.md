# Hearthbound v0.7.6 — completion-aware finite work

## Change
SableAutoWork persists the UUID of an assigned hauling job and no longer
confuses "HAUL_ASSIGNED" with a completed transfer. On a decision boundary,
the routine checks SableHauling.completedJob(citizen, expectedUuid,
configuredDestination), which requires:
- physical executor phase COMPLETE;
- the same job UUID and destination;
- no remaining cargo in the villager job state.

Only when that condition holds is haulCompleted persisted. Once a haul is
issued, WorkOfferLifecycle.canAdvance prevents subsequent autonomous work
until verified completion. This remains true across restarts and quarantine.
Reconfiguring the experiment explicitly resets its finite-work state.

The status command now exposes haulIssued, haulCompleted, and haulJob.

## Verification
The WorkOfferLifecycleTest now includes four completion-gate checks (12 total).
A local Java 17-compatible compile and execution of the pure lifecycle
test was performed successfully: 12 checks passed.

## Caveats
A completed haul here is a *job-state predicate*, not independently
audited inventory conservation. The original SableHauling mill experiment
receipts and audit systems remain authoritative for experimental research
credit. An interrupted/paused/quarantined job remains blocked rather than
being resubmitted; explicit operator recovery is still necessary.

Full Forge compilation and real Minecraft gameplay are not yet verified.
