# Live policy runner v0.2

The Minecraft runner is deliberately opt-in. Use the nearest configured First Mill worker:

- `/hearthbound agent_policy_enable`
- `/hearthbound agent_policy_disable`
- `/hearthbound agent_policy_status`
- `/hearthbound agent_policy_dump`

Enabling the runner pauses only the legacy high-level First Mill scheduler for that worker. Existing navigation, reservation, dwell, capacity, persistence, and item-transfer controllers continue unchanged.

Inference is bounded to at most once every 20 ticks. It sleeps while a haul/travel operation is active and after the flour target is reached. Every decision goes through the stale-safe Minecraft executor.

A bounded in-memory ring retains the most recent 256 decision traces per worker. Each trace records schema, worker, world version, fixed observation vector, chosen action, executor outcome, and acceptance. Traces are also emitted as `HB_AGENT_TRACE` server-log witnesses. This is a control trace; asynchronous delivery rewards will be joined in a later outcome-attribution slice.

Only the scripted v0.2 baseline is selectable here. Learned MLP control remains disabled until offline training and parity evaluation pass.
