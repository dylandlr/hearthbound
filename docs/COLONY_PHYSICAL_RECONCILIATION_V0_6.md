# Colony physical reconciliation diagnosis v0.6

This is a **read-only investigation** of the four-citizen Forge acceptance regression first observed on the v0.5 branch, run 45082837978. Existing Forge compilation, Java contracts, pickup/restart controls and Create causal workflows passed on that revision; the four-citizen CI run reached the live world but finished with `done=3 assigned=1` while all four source chests were empty, destination chest contained four wheat, and source claims were zero. This is an **accounting mismatch to investigate**, not evidence that no wheat was delivered and not proof of an observation-history defect. Do not change action or recovery behavior merely to satisfy the harness.

## New operator-only read-only command
`hearthbound-colony physical-reconciliation-audit` separates `assigned`, `assigned_loaded_incomplete`, `assigned_loaded_physically_complete`, `assigned_unloaded`, `done`, `done_loaded`, `done_unloaded`, history count, and capacity denials. It checks currently loaded villagers using existing `SableHauling.completedJob` but cannot inspect unloaded citizen NBT. A bounded anomaly listing contains task and citizen IDs. The command mutates neither a task, citizen, nor inventory.

## Updated live experiment
The four-citizen RCON harness queries reconciliation at poll 20, 60, and 100, at terminal failure, and at success. It still demands the original four physical deliveries and exact independent inventory/decision/history/trace invariants. It **never** repairs or retries failed jobs. The read-only query can distinguish a physically completed assigned job from an unfinished motor, an unloaded executor, and a stale history audit.

## Next decision gate
Run live acceptance. If `assigned_loaded_physically_complete>0`, study why the colony task transition is delayed without changing the physical motor. If `assigned_unloaded>0`, study chunk/lifecycle handling and preserve the restart fence. If `assigned_loaded_incomplete>0` but destination inventory has four items, investigate multiple source-to-destination job traces and avoid assuming each item maps to one recorded decision. Only integrate a targeted correction once reproducible physical evidence supports it.

No persistence or crash-atomicity guarantees are added here; MARBLE-style individual contribution and societal emergence remain unproven.
