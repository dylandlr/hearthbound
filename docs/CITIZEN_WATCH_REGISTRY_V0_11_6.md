# Hearthbound v0.11.6 — bounded per-citizen source watches

Experimental stacked milestone on PR #136, retaining read-only neural policy and no automatic discovery, planning or movement.

The new CitizenWatchRegistry is independent of the legacy Sable-only LivePerceptionReceipts monitor. Registration requires an operator, an individually marked villager in the same dimension, a loaded source chunk and distance no greater than 16 blocks. It supports at most 24 watch pairs per level and four watched source positions per citizen. Each (citizen UUID, source position) pair owns its own revision counter, prior sample, and latest receipt; there is no global observation broadcast. A Forge END level-tick sampler runs every five game ticks and skips unloaded chunks, missing/dead citizens and UNKNOWN observations. Receipts are session-local and do not authorize actions; the same verified source snapshot refreshes only the observer's own persistent entity knowledge.

## Operator commands

- `/hearthbound citizen_watch <source> <citizen>`
- `/hearthbound citizen_unwatch <source> <citizen>`
- `/hearthbound citizen_watch_latest <source> <citizen>`

All require permission level 2. No chunk-loading, auto-task execution, LLMs, CNNs, shared inventory knowledge or self-selected subscriptions are introduced.

## Dedicated Forge acceptance

The existing two-arm RCON script first verifies two citizens with distinct direct and reported knowledge. It then registers only the recipient to watch its second real chest, requires a three-wheat receipt from server ticks, checks Sable has no subscription receipt, mutates the chest to two wheat, requires a second receipt and updated recipient memory, unregisters the watch, and restores the three-wheat fixture before existing server restart-isolation assertions. Both SCRIPTED and TRAINED_MLP arms must pass.

## Outstanding work

Watch registration is not autonomous. Watch subscriptions are session-local, and stale private memory remains on citizen NBT when sampling stops. Automatic source discovery, occlusion/line-of-sight semantics, world-clock rollback epochs, bounding sampler CPU cost at high citizen counts, and social policy experiments need separate milestones. Existing SourceWheatObservation considers distance and loaded source capability but does not yet prove visual line-of-sight.
