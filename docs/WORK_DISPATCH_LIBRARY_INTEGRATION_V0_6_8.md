# Hearthbound v0.6.8 — live library dispatcher integration

## Implemented server path
The previously standalone CitizenWorkDispatcher is now used by
LibraryPolicyBridge.consider for the STUDY action:
1. Build a server-side action observation and choose with ColonyPolicy.
2. Pass the proposal to CitizenWorkDispatcher for ActionGate validation.
3. Acquire the unique task lease before invoking the Minecraft executor.
4. Recheck actual library inventory; start AutonomousLibraryStudy.assign.
5. Persist the lease ID in villager persistent NBT.
6. On citizen tick, reconcile study completion/interruption and release the lease.

Existing custom hauling checks remain enforced before offering study or
starting the task. Rejecting a physical assignment releases the tentative
lease within the dispatcher.

## Boundaries not yet completed
- The shared dispatcher currently owns the policy-driven STUDY path only.
  Existing hauling assignments are still independently managed.
- Legacy `/hearthbound library assign` and `study` bypass this new lease.
- The singleton dispatcher holds active leases in memory. A restart preserves
  citizen study NBT but not the in-memory arbiter state; lease reconciliation
  clears terminal saved tokens after restart. A final implementation must
  rehydrate and partition arbiter state by world/server instance.
- Need persisted citizen needs and full job candidates (HAUL vs STUDY),
  then explicit emergency preemption, cancellation, and restart test coverage.
- Authenticated lesson is a marker-based dev test; production guidebook
  provenance and source verification are not done.
- No successful Forge compilation/gameplay capture is claimed for this slice.

## Regression acceptance plan
1. Enable library auto, provide tagged milling primer and watch real navigation.
2. Ensure Study Task lease is not duplicated on repeated policy ticks.
3. Remove book during study and inspect terminal state + lease release.
4. Check repeated study cannot grant duplicate knowledge.
5. Make hauling active and ensure no study path is accepted.
6. Restart server mid-study, verify NBT session and no orphaned ownership.
7. Run Forge compile, unit regressions and dedicated server E2E workflow.
