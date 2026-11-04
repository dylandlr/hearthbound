# Hearthbound v0.12.2 — Pre-inspection attention opportunities

This experimental milestone is stacked on PR #142. It records **decision opportunities** on the real Forge server before source-inspection calls, without granting a policy any additional authority.

## Evidence boundary

The existing `CitizenWatchRegistry.sample()` collects at most one selected inspection per marked citizen every five Minecraft ticks. At the selection point, before checking source chunks or invoking `SourceWheatObservation.inspect`, an operator-readable, bounded session-local record is appended:

```text
ATTENTION_OPPORTUNITY schema=hearthbound.forge-attention-opportunity.v1 tick=<server tick> observer=<UUID> dimension=<key> candidates=<source coords separated by ;> candidate_count=<n> selected=<source> budget=1 policy=LEAST_RECENTLY_SAMPLED inventory_read=false action_authorized=false
```

All candidates derive from **already registered subscriptions owned by that citizen**, not an omniscient world scan. The selected source comes from the existing deterministic least-recently-sampled scheduler. A candidate's inclusion does not imply its chunk is loaded, it is currently in range, that its inventory is readable, or that inspection succeeds. A future dataset should explicitly model these as attempted selections and should never label unobserved options as successful.

## Bounded capture

A ring holds at most 128 opportunities per ServerLevel. Every record is emitted before the selected sensor's inventory read. Only permission-level-2 operator commands may access the ring:

- `/hearthbound citizen_opportunity_latest`: returns one record for reliable RCON attribution
- `/hearthbound citizen_opportunities`: dumps the ring to operator output

The record contains no wheat count, source state, reward, action authorization, neural weights or shared citizen memory.

## Live acceptance

The dedicated-server trial uses the existing two-source recipient fixture. Once subscriptions for chest (9,100,2) and chest (10,100,2) are registered, it polls `citizen_opportunity_latest` until a real server-tick opportunity contains both registered candidates. The acceptance requires budget 1, the scripted scheduling policy, and `inventory_read=false`, and rejects any `wheat=` or `state=` data in the pre-inspection record. Existing private-memory and restart tests remain active.

## Limitations

This is not learned decision-making. Its candidate set is a list of operator-registered subscriptions, **not** a claim that the agent could inspect all candidates physically at that moment. No counterfactual outcomes are inferred for unselected candidates. The ring is ephemeral, not a complete continuous-run audit; a future logger should capture each record alongside selected sensor outcome, server tick, citizen identity, and a run ID in an append-only artifact. Do not promote this to a learned controller before those contracts pass.
