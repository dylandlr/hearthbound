# v0.7.18 — Verified citizen machine memory

The genuine dedicated-server production probe passed in PR #92: a powered Create millstone consumed a wheat item and its actual inventory yielded one `create:wheat_flour`.

**That probe has no citizen-authorized job.** It still reports `PROCESS_UNVERIFIED NO_RESEARCH_CREDIT`.

This change introduces `CitizenMillMemory`, a small NBT experience ledger on the real Villager entity. `MillProcessReceipts.record` calls it **only after** accepting one authorized, untainted machine-processing receipt. Memory fields:
- `observedVerifiedProcesses`
- `lastVerifiedTick`
- `lastMachine`
- `recentJobs` bounded to 128 entries for readback

The authoritative receipt map's one-job rule is the primary duplicate guard; recentJobs is only a bounded secondary guard. The receipt SavedData and villager persistent NBT are not atomically saved together, so memory and receipt may diverge on crashes. This is observational memory, **not** a trained model, not a durable reward, and not evidence that citizens autonomously discover or reuse recipes.

## Next actual demo
1. Connect Sable's physical wheat insertion to a Create millstone with a reserved, verified job.
2. Capture a server log showing `HEARTHBOUND_PROCESS_RECEIPT` followed by `HEARTHBOUND_CITIZEN_MILL_EXPERIENCE` for the same job.
3. Restart the server and inspect villager NBT and receipt persistence; reconcile any divergence.
4. Train two matched task policies (MLP vs scripted) in the fast simulator and evaluate on held-out Minecraft trials. Only call this *learning* if behavior/performance measurably changes versus an untrained control.
5. Keep autonomous research rewards disabled until journal rollback reconciliation is authoritative.

The code in this PR is pending Forge compilation and in-game validation.
