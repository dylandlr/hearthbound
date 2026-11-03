# Hearthbound v0.11.4 — Explicit local citizen knowledge reports

Status: EXPERIMENTAL, stacked on v0.11.3 / PR #134. No autonomous policy control.

## Contracts
- Sender and recipient must be distinct marked villagers on the same live ServerLevel, separated by no more than 12 blocks.
- The sender must have a directly observed source record from its private knowledge NBT and that record must have been refreshed within 40 game ticks.
- Recipient reports go exclusively into their own persistent Forge entity NBT (`hearthbound.citizen_reports.v1`); no global shared memory or direct-observation forgery.
- Each report includes original source dimension and coordinates, wheat count, original observation tick, source revision, sender UUID, recipient UUID, delivery tick and a separate reported-origin marker.
- Exact repeat delivery of the same sender/source/revision returns DUPLICATE, without adding a second record.
- Reports are bounded to 16 entries per recipient and become EXPIRED after 200 ticks. Retention and freshness do not imply truth or authorization.
- The sender's direct knowledge is separate from the recipient's report. No citizen gets access to the other citizen's cache.
- Both read and share operations remain operator-only for now. Neither command changes inventory, forces chunks, runs movement, or gives the trained MLP permission to execute.

## Operator commands

```mcfunction
/hearthbound knowledge_share 6 100 2 @e[type=minecraft:villager,tag=hb_report_recipient,limit=1]
/hearthbound knowledge_report 6 100 2 @e[type=minecraft:villager,tag=hb_report_recipient,limit=1]
```

`knowledge_share` uses the single marked Sable near the source as sender. In this iteration only Sable receives live observations from the perception watcher; an arbitrary marked citizen cannot yet become a direct-source observer. That is a known v0.11.5 dependency.

## Dedicated server acceptance

In both SCRIPTED and TRAINED_MLP existing Forge-server arms, following the real empty/4 wheat/empty perception sequence:

1. Re-register the source watch so Sable holds fresh direct evidence.
2. Summon a disposable second marked villager; prove it starts without a report for the source.
3. Explicitly deliver Sable's direct observation; assert reported provenance, distinct recipient ownership and `action_authorized=false`.
4. Attempt an exact repeated transfer; require `DUPLICATE`.
5. Unregister watch, then continue the pre-existing persistence checkpoint and server restart.

These are required test assertions. Do not claim the social report test has passed until the new workflow actually completes.

## Remaining blockers

- Real live multi-citizen perception rather than one named Sable.
- Simulated social actions, communication budgets, trust scores, contradictory reports and learned sharing policy.
- Dedicated tests for recipient report persistence through restart, range denial, expiry, evictions and heterogeneous roles.
- Chunk/restart/time rollback semantics for report expiry. Historical reports can remain even after the originating source is gone.
- No camera-frame synchronization or CNN results yet.
