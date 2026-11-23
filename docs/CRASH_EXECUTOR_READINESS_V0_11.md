# Original executor readiness after a forced crash

## Observed validation failure

The `AFTER_DELIVERY_RETURN` compatibility check failed on both
[the first #213 revision](https://github.com/dylandlr/hearthbound/actions/runs/45132603140/job/137551307417)
and [its fixture-readiness follow-up](https://github.com/dylandlr/hearthbound/actions/runs/45133375444/job/137553790348).
Both failures are retained. The original verifier queried the restored
citizen immediately after reading the journal and inventory baseline, and
treated any response other than an absent haul field as an unexpected
restored assignment. In these runs the response was instead `No entity was
found`. That does not establish whether the citizen was still loading or
failed to persist.

For the first failure, the server reported ready about 1.84 seconds before
the entity query. The initial setup had also needed several read-only polls
after spawning before its selector found the executor. Baseline entity-region
files were not retained in that artifact, so the old evidence cannot settle
loading versus persistence. The new gate must not silently treat either as
success.

The durable journal and restored source/destination baseline passed their
checks. At `AFTER_DELIVERY_RETURN`, the server is deliberately killed after
the journal records insertion return but before cargo removal, the motor's
COMPLETE phase, claim release, or the new colony completion callback. The
callback therefore cannot execute before this forced kill. This test-only
follow-up leaves all Minecraft runtime code unchanged.

## Bounded identity-specific verification

The verifier now identifies the original executor from the saved dispatch
and validates that identity against the durable job receipt. It polls within
a ten-second readiness acceptance window for that exact UUID after restart.
A response arriving after that deadline cannot pass; a blocked RCON request
retains the existing transport timeout and may take longer to fail. The wait
performs read-only entity queries; it does not spawn a substitute, teleport,
force chunks, dispatch a task, repair a save, or repeat a motor operation.

If the original executor remains absent, verification fails explicitly with
`MISSING_BASELINE_EXECUTOR`. Once it is available, the original strict check
still requires that the unsaved hauling assignment be absent. A different
citizen named Sable cannot satisfy the identity check. A restored haul field
still fails. All existing world, journal-state, delivery-state, inventory,
no-retry, and no-reward assertions remain in force.

This changes a startup precondition and failure diagnosis, not the expected
crash outcome. A passing corrected test establishes that its recorded
executor returned within the bounded window and its unsaved assignment did
not; it does not retroactively establish why either archived run failed.

## Validation and relation to colony reliability

Unit checks exercise delayed availability, the exact executor UUID,
identity mismatch, timeout, and rejection of an unexpected haul field. The
existing six-boundary Forge matrix tests the complete forced-kill/restart
flow on the explicit proposed head. It retains each journal, checkpoint,
server log, RCON log, and verification result.

The production hauling code and the five-world colony fixture are unchanged
from #213. Its two complete cohorts remain separate: five passes at
`ec7498d3e41f8f472faf9b35b74af1415dba88f7`, and four passes plus one missed
source at `b8e427863bf9562372c8b0a5364c5ec7168e1c95`. Each observed zero of
the exact historical and broader accounting events in five assessable
worlds, with a descriptive 95% Wilson interval of 0–43.45%. The missed-source
trial remains failed, and the overall reliability issue remains open.

See [the delivery reconciliation contract](COLONY_DELIVERY_RECONCILIATION_V0_10.md)
for runtime behavior and the separate accounting/discovery distinctions.
