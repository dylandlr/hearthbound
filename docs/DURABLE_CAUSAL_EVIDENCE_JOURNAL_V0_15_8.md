# Hearthbound v0.15.8 — Durable Causal Evidence Journal

## Overview

This milestone introduces an append-only, world-save-scoped **evidence-only** journal; it does not credit rewards, teach technology, modify inventory or train neural agents.

The permission-2 operator command is `/sable mill-outcome-journal <job-uuid>`. It joins the actual Sable executor assignment with the actual Create `process()` callback, current untainted mill reservation, and durable per-world UUID. Event IDs are derived on the Minecraft server, not supplied by the operator.

## Binary safety contract

- Header: `HBCJ` magic, version 1, world UUID and CRC32.
- Each frame: contiguous sequence, previous-frame SHA-256 digest, typed transition, CRC32 and bounded length.
- OS-level single-writer file lock, fsync before state change, write-failure poisoning.
- Strict recovery: refuse corrupt CRC, broken chain, duplicated evidence, invalid transitions or torn frames. No silent tail truncation.
- `OBSERVED`: physical evidence copied into the append-only log.
- `ADMITTED`: the physical witnesses were checked. **This is NOT payment authorization**.
- `REVOKED`: a terminal historical invalidation; never re-admitted.
- On EVERY reopen, persisted `ADMITTED` entries lose active trust until live source revalidation succeeds.

## Real Minecraft verification

The first-mill RCON fixture now archives the verified process twice (stable/idempotent), rejects another citizen's attempt to claim it, and requires that release of the original reservation revokes journal admission.

The two-boot Forge restart fixture takes an operator-side baseline, runs `save-all flush`, stops, boots the same world, and requires exact journal evidence continuity after live revalidation. The historic Create callback remains after release even though the journal becomes `REVOKED`.

Standalone Java 17 tests additionally cover world mismatch, locks, corruption, truncation, forged sequences and late-taint reconciliation.

## Important limits

The journal does not make vanilla SavedData, villager NBT and its own file atomic across process crashes. If one store is restored from an older checkpoint, a recovered journal entry must be rejected on live revalidation. Missing/unloaded evidence cannot authorize rewards; this operator-only command avoids revoking a stored event when its machine chunk is not loaded.

Operator invocation is required; it is not an autonomous learning loop or an independently chosen research hypothesis. Rewards, recipes, inbox draining, and neural policy updates remain disabled. A future milestone must test interrupted writes/rollback and authorize deduplicated credit only after strict world-source reconciliation.
