# Hearthbound v0.10.8 — Adaptive sensing instead of arbitrary information quotas

## Architectural decision

No hard refresh quota is required for regular Minecraft citizens. Immediate local observations should be available through normal game-state reads; remote/changing inventories and world observations are cached and can have retrieval cost/latency. The v0.10.7 hard-quota collapse was a stress experiment on an agent *not trained for quotas*, not a reason to impose an artificial numerical limit in normal gameplay.

In the **fast simulator only**, train four comparable upper-level policy networks: a previously frozen age-aware reference, and three new 21→24→4 neural Q networks with per-refresh TD penalties of **0.00, 0.04, 0.12**. No hard quota. All new networks receive the existing 21-dimensional bounded input (including observation age), REFRESH_SENSORS remains a simulated one-step action, and all physical tasks still require independently checked execution-time stock.

The soft cost represents an abstract combination of time/CPU/network/query expense, **not benchmarked Minecraft milliseconds or money**. The original environment's personal/colony rewards are reported unchanged, and the training-only penalty is separately selected by configuration. Training includes failed-refresh and stock-drift perturbations; the outer evaluation uses novel delay lengths, existing frozen comparators and matched episode seeds. The neural network learns a preference for observation effort, rather than receiving a privileged observation or automatically being denied after a fixed number.

Success must be interpreted jointly with fresh observation requests, supervisor rejections, valid proposal rate and task completion. A model with fewer refreshes but no flour production is not a better agent.

## Caveats

The new models are trained with synthetic failures and drift, but the Minecraft execution controller, Forge observation contract and biological/social cognition remain unchanged. There is **no LLM**, no Minecraft neural-policy rollout, and no demonstrated emergence from this experiment. For actual game performance, eventually profile cost per observation type and implement caching, event subscriptions and colony information exchange, while keeping server authority independent of what a citizen believes.
