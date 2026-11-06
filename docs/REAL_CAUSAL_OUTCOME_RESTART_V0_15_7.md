# Hearthbound v0.15.7 — Real-world causal evidence restart acceptance

This is **not** a new reward authorization or a new write-ahead evidence journal. It is the next empirical admission gate: show that the three existing *independently persisted* witnesses still join into **the exact same causal outcome after a genuine Forge server save, shutdown and reboot**.

## What the fresh-world acceptance performs

1. Boot actual Forge/Create with Sable's first-mill physical hauling fixture, one reserved machine and the authoritative world-save UUID.
2. Require a direct Create wheat-to-flour callback, a completed executor assignment with its real game-time tick, and a still-held, untainted lease.
3. Query the read-only v0.15.6 mill outcome proposal, including its physical evidence ID; record the complete operator-side output to a reference JSON file that is **not accessible to the citizen**.
4. Run `save-all flush`, stop the Minecraft server, and wait for its process to terminate.
5. Reboot that **same world** and re-check raw process receipt, held lease, and the exact identical citizen/world/assignment/processing/physical-evidence proposal bytes.
6. Repeat the proposal after restart, reject an unknown job, then explicitly clear mill output and perform an operator-reviewed reservation release. The original callback remains a historical record while proposal eligibility must be denied.
7. Upload both real server logs and RCON transcripts.

## Interpretation

- Passing will establish **graceful save/restart reproducibility** of the existing separate persistent stores, not crash-atomic cross-store transactionality.
- The write-only operator reference `mill-outcome-pre-restart.json` is a test oracle, not part of the colony's state, a data channel for agents, or evidence of neural learning.
- The current value of 500 personal milli-points remains only an **engineered proposal**. Colony/research rewards are zero and `reward_authorized=false`.
- A released lease must invalidate any future proposal even when the direct Create callback remains historically true.
- Any missing, tainted or contradictory witness should cause denial, never inference or ledger payout.

## CI

Run GitHub Actions workflow `.github/workflows/real-outcome-restart.yml` on this branch; it executes the two-phase real Minecraft test, not a mocked Java state machine.

## Next phase: real append-only journal with reconciliation

After this gate passes, implement a world-bound append-only outcome envelope with monotonic sequence, hash-chain or checksummed framing, and explicit states `OBSERVED -> ADMITTED -> REVOKED` (no payout). Recover and cross-check world UUID, current reservations, process receipts, citizen assignment, and taint markers on restart. The journal must not assume atomicity with separate vanilla SavedData and villager NBT, and must fail closed on any inconsistency.

Only later may we enable constrained, deduplicated durable delivery and measure real post-training policy changes against scripted controls.
