# Actual citizen communication records, v0.1

This revision extends the existing local source-report exchange and operator-triggered report-based hauling experiment. It records actual Minecraft activity. It does not yet add autonomous message generation, choose a communication topology, or establish a performance advantage from collaboration.

## Recorded evidence

`CitizenCommunicationRecords` persists a bounded history in the dimension's SavedData. Every accepted delivery has its own message UUID, world UUID, server episode, sender, recipient, source-report identity, source location, reported wheat, source revision, observation tick, sent tick, and delivery tick. Transmission is currently synchronous, so sent and delivered ticks coincide. The payload remains a report of a prior observation, not current inventory truth.

Send attempts retain the actual sender, recipient, source, tick, and outcome: `REQUESTED`, `REJECTED` with reason, `DUPLICATE`, or `DELIVERED`. Invalid participants, range failures, missing/stale observations, and restart fences retain their existing behavior. Repeating an already-delivered report does not refresh its age or create a second delivery. Expiry is explicit in the delivery record; the history remains available after the recipient's inbox entry expires or is evicted.

The pure Java `CommunicationJournal` validates these separate stages:

| Stage | Actual hook | Meaning |
|---|---|---|
| `DELIVERED` | Recipient inbox updated | A particular citizen received the report. |
| `READ` | Actual dispatch policy consumes an admissible recipient report | This report was an input candidate. Operator inspection and shadow evaluation do not create this event. |
| `SELECTED` | Policy selects a source bound to that report | The report was selected for this decision. Assignment may still be rejected. |
| `ASSIGNED` | Existing hauling executor accepts a job | The selected report and decision are linked to a real citizen/job/source/destination. |
| `PHYSICAL_COMPLETED` | Existing executor inserts cargo successfully and releases its source claim | The linked motor job completed; this is an executor receipt. Independent before/after chest checks remain separate evidence. |

A report may be read but not selected, and an assignment may remain incomplete. Absence of a later event is unresolved: this version does not distinguish every policy abstention, assignment rejection, motor failure, timeout, and interruption in a terminal decision record. It must not be used as a complete usefulness-rate denominator. The withheld control's command receipt is retained by the acceptance fixture; withholding creates no false report reads or uses.

## Boundaries and persistence

The history never supplies policy inputs, performs inventory operations, authorizes work, or grants rewards. Source visibility, range, freshness, report-session fences, source claims, pickup/delivery journals, and Create safeguards remain in their existing paths. The autonomous four-citizen policy still uses its existing local observations.

The history retains up to 1,024 delivered messages, 8,192 lifecycle events, and 2,048 send attempts. It does not silently evict evidence. Capacity denials and recording errors are visible in the audit; missing records must remain missing in analysis. Invalid saved history is preserved and quarantined instead of being treated as an empty successful history. Telemetry failure does not block a physical job or authorize its retry.

Clean Minecraft saves preserve history. Restarting creates a new episode, so old reports do not become fresh decision authority. Ordinary SavedData persistence does not establish crash-atomicity with inventories or the existing durable pickup/delivery journal. A complete message-to-job trace supplies attributable association; controlled independent-world comparisons are still required for a causal benefit claim.

## Read-only operator export

All commands require operator permission level 2:

```text
hearthbound-communication audit
hearthbound-communication attempts 0
hearthbound-communication messages 0
hearthbound-communication events 0
```

The numeric argument is an offset. Attempts/messages return up to four records; events return up to eight. Continue from the number of records already collected until `total` is reached. The acceptance exporter checks that totals and the audit remain unchanged during export. Every page labels independent inventory verification and causal benefit as false; those claims cannot be inferred from this journal alone.

## Validation

The pure journal suite covers counterfeit recipients, chronology, lifecycle prerequisites, per-recipient message identity, conflicting/idempotent replays, job/decision reuse, bounded capacity, and validated restoration. Python acceptance-validator tests reject mixed jobs, actors, worlds, episodes, and impossible outcomes.

`.github/workflows/real-citizen-communication.yml` tests the proposed head revision in a fresh Forge world. A marked scout observes two real wheat sources, sends two reports to another real citizen, and the scripted policy reads both, selects one, and assigns a physical hauling job. The fixture separately verifies source A changes from 3 to 2 wheat, source B stays at 1, and the destination changes from 0 to 1. Shadow inspection and a withheld-report dispatch must leave the history unchanged. A second server lifetime must preserve records and abstain from acting on old-session reports. Failures retain raw logs and a structured diagnostic artifact where the server remains reachable.

Artifacts are `citizen-communication-before.json`, `citizen-communication-after.json`, diagnostic failure JSON when applicable, and server/RCON logs. This is a scripted acceptance fixture with a fixed menu, not an autonomous network experiment. The independent-world accounting pilot is documented separately in [COLONY_RELIABILITY_TRIALS_V0_1.md](COLONY_RELIABILITY_TRIALS_V0_1.md). Research motivation and limits are in [PROJECT_SID_PA4_RESEARCH_FOUNDATION.md](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md).
