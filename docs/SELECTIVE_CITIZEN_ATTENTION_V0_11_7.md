# Hearthbound v0.11.7 — Scripted selective-attention baseline

This experimental milestone builds on v0.11.6's independently validated per-citizen Forge watches. It does **not** introduce an ML-selected action, autonomous subscription, unbounded scanning or new task authority.

## Behavior contract

- Each marked citizen can have up to four operator-registered source watches, with at most 24 watch pairs per ServerLevel.
- An individual citizen spends **at most one** source-inspection attempt per 5-game-tick sampling interval, regardless of the number of subscriptions. Each selected attempt consumes the budget even if the chunk is unloaded or the citizen is absent.
- Deterministic scripted scheduler sorts by citizen UUID, then least-recently-attempted watch, then source XYZ. This is a fair round-robin reference with explicit cost; it does not use machine learning or hidden world state.
- Only selected watches query the existing source sensor. Known snapshots refresh the same citizen's private NBT, with independent per-(citizen,source) receipt revisions.
- `/hearthbound citizen_attention <citizen>` is operator-only and reports subscriptions, budget, interval, and policy. No task authorization is granted.

## Acceptance

The two existing real Forge arms must continue passing legacy Sable source perception, private citizen knowledge, explicit social report, separate recipient direct observation and save/restart isolation. The new RCON extension provisions another real chest, registers the recipient to observe two physical sources, verifies `subscriptions=2 budget=1 interval_ticks=5`, and waits for independently tagged receipts from both. Sable must remain unaware of the comparison source.

## Limitations

This is *not* learned selective attention. Watch registration remains operator-driven. The source sensor checks distance, loaded chunks and inventory capabilities but does not yet establish unobstructed line-of-sight. No world-generation discovery, attention-policy training, action execution, client RGB capture, or held-out generalization is claimed. Timing and CPU budget must be benchmarked as citizen counts scale; receipt timestamps plus an independent server log should be used for performance claims. Social policy comparisons should wait until this baseline is verified.
