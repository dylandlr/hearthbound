# Hearthbound v0.11.2 — Dedicated Forge perception acceptance

## Goal

Advance from v0.11.1's **compiled, read-only source sampler** and synthetic receipt-contract tests to actual dedicated-server acceptance. A reproducible Forge 1.20.1/Create RCON test must demonstrate a real inventory observation sequence **EMPTY → AVAILABLE(4 wheat) → EMPTY** for a physically present, marked Sable. Receipt revision, source, dimension and server-tick fields must be validated from the server's actual responses.

## Implemented acceptance

The existing `.github/workflows/dedicated-server-smoke.yml` now performs the additional test in **both SCRIPTED and TRAINED_MLP policy arms**, after the original Minecraft millstone and hauling tests and before saving/restarting the world. This is a test-environment test: it does not dispatch new experimental neural options. The script:

1. Uses the already started disposable Forge dedicated server and authenticates over RCON.
2. Teleports an existing named Sable to a test observation location, sets a separate chest to empty, and registers an operator-only `perception_watch` source.
3. Polls the dedicated read-only `perception_latest` command until a genuine server-origin, revisioned EMPTY receipt appears.
4. Changes the actual chest NBT to four wheat, requires a new AVAILABLE receipt, then empties the chest again and requires a third EMPTY receipt.
5. Requires consecutive monitor-local revisions and monotonic server ticks; checks source coordinates and dimension.
6. Exports actual RCON receipts to `real-perception-receipts.txt`, an explicit real-Forge summary to `real-perception-acceptance.json`, and a separate strict parser validation to `real-perception-validated.json`.
7. Unregisters the observation watch without changing task authority. The original Sable experience/persistence checks run afterwards.

One receipt per RCON response is returned through the new `/hearthbound perception_latest` command. This avoids dependence on how Minecraft RCON serializes multiple separate command-chat messages. The original bounded `perception_receipts` history command remains for operator inspection.

## Verification claims

- CI must **actually boot Forge**, place and mutate a chest, and receive three real Forge receipts before the new milestone is considered accepted.
- The test intentionally changes a disposable chest by an operator command; this is **not** autonomously discovered or mutated by a citizen.
- Receipt revision is a transient observation-monitor version, never permission to transfer items. It may reset after server restart and is not a general inventory transaction version.
- No camera images have yet been captured, no CNN/ViT trained, and no visual-only Minecraft agent is enabled.

## Next milestone

If the live RCON acceptance passes, expand to measuring latency and sampling cost in ticks, proving chunk-unload and restart semantics, then connect the read-only receipt stream to a **separate, permission-scoped personal knowledge cache**. In parallel design a real client RGB capture with camera/tick alignment; avoid calling rendered camera data authoritative inventory evidence.
