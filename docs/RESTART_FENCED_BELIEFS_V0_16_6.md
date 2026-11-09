# v0.16.6: clean-save beliefs and conservative restart fencing

Incremental Track A of [issue #191](https://github.com/dylandlr/hearthbound/issues/191),
stacked on [PR #190](https://github.com/dylandlr/hearthbound/pull/190).

## Behavior

Each real server lifetime creates a random, runtime-only report session bound to
the saved world UUID. A real local `CitizenSourceKnowledge.remember` observation
records that world/session. Sharing copies those fields; it never renews them.
Report identity includes the session so a rolled-back tick cannot collide with a
new physical observation. Historical NBT remains available for inspection.

Both scripted and frozen MLP policies use the same recipient-report accessor.
After every restart, old and legacy reports are unavailable for source choices
until the scout actually observes and delivers new evidence. This includes an
executor whose unsaved negative record disappeared. No chest is queried by the
choice filter. Restart is an engine safety boundary, not an omniscient policy
feature. This conservative rule also discards otherwise useful positive reports.

Restored unpicked **report-policy** motor tasks pause before extraction, closing
the alternate path around that filter. Their job and report provenance remain
unchanged. Existing cargo quarantine remains in force; this change never cancels
or retries cargo-bearing jobs. Legacy non-policy haul behavior is unchanged.

Unpicked cancellation now has its own terminal state and reports CANCELLED,
never EXECUTOR_COMPLETED. Completion additionally requires a timestamp written
only after actual insertion returned no remainder. Older saves used COMPLETE
for both cancellation and delivery, so legacy completion without this marker is
unverified. This is an executor receipt, not a substitute for independent
inventory-delta checks or a claim of crash-atomic transfer.

Failure/request validation rejects foreign-world or foreign-executor records,
future events, duplicate jobs, oversized/malformed lists, wrong NBT scalar types,
and requests whose failed job, source, report ID or timestamps disagree. A
fulfilled request cannot be reissued for the same failure. A pending request is
not overwritten by another source request. A new direct report is still required
for fulfillment; request creation never dispatches or observes for a scout.

## Real-server acceptance

Workflow: `real-pickup-belief-restart.yml`; evidence artifacts:
`pickup-belief-restart-clean` and `pickup-belief-restart-crash`.

1. **Clean:** actual A extraction fails, explicit recheck stays pending; save,
   stop, restart the same world. Compare complete failure/request/haul NBT and
   world/executor/job/report/tick identities. Require no completed failed job,
   both policies rejecting preboot reports, and no old scout memory renewal.
   Exercise foreign identity and malformed-record controls with a fresh B report.
   A real new scout observation fulfills the request. A distinct job must deliver
   B physically, with independent A=0, B=0, destination=1 checks.
2. **Forced kill before save:** flush the old reports before dispatch, disable
   saving, genuinely fail extraction and request recheck, then kill the server
   process group without `/stop`. Reboot and require the negative/request/job to
   actually be absent. Both policies must abstain even with missing negative NBT;
   only new local observations restore source choice. This control does not claim
   a physical recovery delivery or surviving failure history.
3. **Different world identity:** copy the stopped clean checkpoint into a separate
   disposable world, preserve citizen data, and remove that copy's world-identity
   SavedData. On boot, require a different world UUID and identical citizen
   failure/request NBT. Even newly observed local B reports cannot bypass the
   foreign negative evidence. No automatic evidence repair occurs.

The CI script uses outside-world JSON only as an assertion baseline. Citizens
never read it. Adversarial NBT edits are labeled test controls, not observations.
Local standalone tests target Java 17; authoritative Forge and Linux Java 17
results are supplied by CI at the PR's exact head commit.

## Limits and next implementation

This is **not fsync durability for pickup memories**, an atomic item transaction,
or authoritative reconciliation of the last extraction. A crash can still lose
the exact failed-job receipt and pending request. The boot fence prevents old
reports becoming usable in that case; it does not recreate missing history.
Same-session unsaved corruption, cargo transactions and full save rollback need
separate durable transaction work. Restoring a full backup must preserve its
world identity and matching journals; it must not selectively restore files.

Next: introduce a world-bound extraction-intent/outcome journal with a forced
intent record **before** the motor operation, an outcome after the real call,
and a quarantine state for unresolved intent. Exercise every interruption
boundary, disk/write failures, missing journals, mixed rollback and loaded/unloaded
citizens. Do not restore credits, infer empty inventory, or replay transfers from
absence of an outcome. Exact negative history recovery remains open in #191.

Then implement Track B's internal `REQUEST_REOBSERVATION` / `WAIT_FOR_REPORT`
task options, scout acceptance under local perception and active-task constraints,
and requested/accepted/observed/delivered/expired states. Until those trials pass,
all recovery here is operator-triggered. No LLMs, new gradients, social rewards,
Create research credit, technology unlocks, autonomous-society claims, or claim
that the MLP outperforms the scripted baseline.

See [the society and multiplayer readiness roadmap](SOCIETY_AND_MULTIPLAYER_ROADMAP.md).
