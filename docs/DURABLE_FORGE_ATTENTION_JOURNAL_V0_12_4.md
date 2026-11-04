# Hearthbound v0.12.4 — Opt-in durable Forge attention journal

This draft milestone extends PR #144's validated choice/outcome evidence with **real on-disk, run-scoped recording**. The existing 128-entry in-memory rings remain useful for operators but are explicitly not sufficient for longer experiments.

## Recording contract

An operator starts and stops a recording with:

```text
/hearthbound citizen_log_start
/hearthbound citizen_log_status
/hearthbound citizen_log_stop
```

All require permission level 2. Recording is **disabled by default**. A start creates a fresh file under the Minecraft save's `hearthbound-attention/attention-<run-id>.jsonl`, refusing to overwrite any existing file. Every completed selected inspection generates exactly one append containing its earlier ATTENTION_OPPORTUNITY and subsequent ATTENTION_OUTCOME. Failed inspection attempts are recorded with `UNOBSERVED`, unknown state, and no resource amount. Unselected candidate outcomes remain unknown.

Each record contains the schema, UUID run ID, monotonically increasing sequence, prior SHA-256 digest, base64url payload containing *only the two source event strings*, and the next SHA-256 digest calculated over the previous digest, newline and encoded payload. The initial chain value is `GENESIS`. A session is capped at 50,000 records; cap or I/O failure disables further recording and is surfaced in operator status. A new start always creates a distinct run ID and file.

## Durability and performance limits

`Files.writeString(..., APPEND)` writes a complete JSONL entry on the main server thread, and the event is counted **only after** a successful write call. It is not fsync: the operating system may lose recently buffered records after power loss. SHA-256 detects changes to the retained chain or reordered/missing interior records, but **cannot** detect truncation of the final records without a trusted external final digest. The recording is opt-in to control disk and tick cost; production-scale research should migrate to bounded asynchronous writer queues with backpressure and explicit flush/close receipts, and measure TPS impact. No user-accessible arbitrary file path is accepted; all paths are generated beneath the world directory.

## Acceptance

The existing two-chest real Forge RCON scenario starts the log before registering a pair of source watches and stops it before server shutdown. Both SCRIPTED and TRAINED_MLP dedicated-server CI arms then discover the saved file and verify:
- Run ID matches its filename; sequences start at 1 and never skip.
- Every entry is a valid pre-choice/actual-outcome pair matched on server tick, observer UUID, selected source, and dimension.
- Hashes form an unbroken SHA-256 chain, with no source inventory or counterfactual reward leaked into pre-choice records.
- At least two actual source-inspection attempts were recorded.
- No Minecraft actions, neural-controller execution, or counterfactual reward claims.

Artifacts: `run/**/hearthbound-attention/*.jsonl` and `verified-attention-journal.json`, alongside existing per-run RCON evidence.

## Next steps

Capture an explicit trusted end-of-run digest, restart recovery receipts, and a session-index manifest before considering full-lifetime datasets. Verify the logger does not degrade dedicated-server tick latency under representative citizen counts. This is **not** yet autonomous source selection.
