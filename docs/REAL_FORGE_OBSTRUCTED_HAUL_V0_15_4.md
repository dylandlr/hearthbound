# Hearthbound v0.15.4 — Obstructed real Forge hauling

The preceding two-citizen physical Forge acceptance in PR #174 passed on run 42279368820. Its actual server RCON transcript confirmed two spawned villagers, a rejected shared-source assignment, two independently held source claims, two wheat deliveries (each source 8→7 and destination 0→1), released claims and both villagers near their destination. This validates only the unobstructed flat world.

## New causal intervention

Test in a separately created disposable Forge world. Construct a **sealed corridor** with floor, side/end walls and roof, divided by a three-block-wide, three-block-high solid stone barrier at x=9. Put citizen A and its stocked source chest at x=12 and x=11 respectively, and its empty destination chest at x=7 on the opposite side of the barrier. The barrier exists before task assignment, preventing a race where citizen A completes delivery before obstruction is installed.

Citizen B is spawned outside this corridor at x=22, with separate stocked source x=24 and destination x=19. Assign both jobs while the barrier is intact. The source-claim ledger must initially report two active claims. Citizen A must **actually extract one wheat** and hold it (RCON audit `phase=1`, `cargo=1x...`, `claim=owned`), while B must independently complete its physical delivery (source 8→7, dest 0→1, claim released).

After an additional server interval under the barrier, require A still has cargo, its destination chest remains truly empty, its source contains seven wheat, its source claim remains owned, and B's own source claim is released. Verify x=9 remains stone. Only then issue an explicit operator `fill ... air` to remove the barrier. Require A to physically deposit its wheat within 75 two-second polls, both final source/destination counts to be correct and both source claims to be absent. Verify a villager physically reaches each destination.

The algorithm never reads this intervention as input; it has no access to RCON privileged truth. The experiment is a scripted-task **embodiment reliability** fixture, not a learned policy experiment. No neural weights, runtime Sable hauling behavior, crafting, LLMs or claim repair mechanisms are changed.

## Test gates and limits

`scripts/test_rcon_obstructed_haul_acceptance.py` validates read-only acceptance checks, held-cargo conditions, physical chest counts and claim ownership fail-closed. `.github/workflows/real-obstructed-haul.yml` compiles Forge, boots a disposable world, runs the real RCON fixture and always uploads logs. Do not declare success until GitHub Actions reports a pass and its transcript shows actual blocked and reopened conditions.

A failure due to geometry or pathfinding remains useful evidence; do not weaken cargo or claim checks merely to make the acceptance pass. This is a single obstruction, not an adaptive navigation policy or a statistically robust colony stress suite.

## Verified real Forge result (GitHub Actions 42283209343)

The dedicated workflow passed against a freshly booted real Forge server and saved full `real-obstructed-rcon.log` plus the server log in artifact `real-obstructed-haul-evidence` (artifact ID 13536202618).

- Both actual villager jobs were assigned, with **two distinct source claims**. Citizen A's first observed hauling audit showed `phase=1 cargo=1xwheat`, source x=11 holding seven wheat, destination x=7 empty, `claim=owned`.
- Citizen B physically delivered its wheat to x=19 while citizen A remained behind the solid wall. B's source fell to seven, destination held one, and B's claim was released.
- The evaluator checked that citizen A still held exactly one wheat in its persistent cargo and owned its source, that its destination had **no chest inventory item**, and that x=9 remained `minecraft:stone`. This produced `OBSTRUCTED_HAUL_HOLD_CONFIRMED`.
- After an explicit operator RCON command replaced nine stone blocks with air, citizen A's real destination chest held one wheat on the **first subsequent 2-second poll**. Both final source inventories were seven, destinations one, owner queries returned no claims and both villagers were near their target chests. The workflow emitted `REAL_FORGE_OBSTRUCTED_HAUL_PASS`.

This is one controlled success, not a reliability rate. Its main experimental attribution is that held cargo and source ownership were preserved through a real-world obstruction and delivery resumed after clearance while a separate citizen completed a job. It does not prove that A was unable to reach destination by any imaginable route under different geometry, nor does it prove this behavior for large settlements, persistent crashes, hostile mobs or high-latency multiplayer.
