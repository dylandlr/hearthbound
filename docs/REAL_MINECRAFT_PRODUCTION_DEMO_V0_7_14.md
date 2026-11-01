# v0.7.14 — Real Minecraft Create production evidence gate

## Observed results
The research-journal CI passed all 73 checks. Forge compilation, dedicated-server smoke and playtest JAR builds passed on the same commit. The dedicated-server smoke showed Sable spawned and a chest hauling job assigned, but `MILL NOT_CREATE_MILLSTONE` and **no real Create production receipt**.

## Required demonstration
1. Boot Minecraft 1.20.1 + compatible Forge/Create + tested Hearthbound JAR on a real dedicated server and connect a real client.
2. Place and power an authentic Create millstone, shaft and source with a legitimate wheat input; use the experimental Sable job flow.
3. Capture the server log and screen recording identifying commit, mod versions and policy.
4. Run `python3 scripts/verify-real-mill-production.py <server.log>`. The report must show `production_verified: true`.
5. Confirm actual in-world flour ItemStack from server inventory and capture screen/video corroboration. The log-only checker is a necessary gate, **not sufficient** on its own for full gameplay acceptance.
6. Restart server, inspect persistent receipt and confirm no duplicate research credit. Research credit remains disabled until safe durable delivery and rollback reconciliation are truly wired.
7. For citizen learning, measure a held-out repeat trial under a trained policy vs an untrained control; hauling or spawning alone is not learning.

## Important limits
The checker matches chronological callback/receipt lines and rejects intervening processing rejection markers; it does not cryptographically bind a callback to a job. Concurrent mills can cause false association; execute one reserved mill at a time for this first demo and add explicit operation IDs to logs later. Synthetic parser unit tests are *not* Minecraft evidence.
