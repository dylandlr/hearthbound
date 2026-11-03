# Hearthbound v0.11.1 — Read-only live Forge perception receipts

## Actual integration

Unlike v0.10.9–v0.11.0's Python-only social-knowledge simulators, this milestone adds a **Forge 1.20.1 server-side sampler** in `LivePerceptionReceipts.java` and an operator-only command surface in `HearthboundMod.java`. The sampler calls the existing `SourceWheatObservation.inspect` on **loaded** source blocks within 16 blocks of exactly one marked Sable villager, at most once every five server ticks. It registers up to 12 explicit source watches per level and keeps at most 96 receipt strings per level in transient memory.

Commands (permission level 2):
- `/hearthbound perception_watch <x y z>`: watch source for observable changes.
- `/hearthbound perception_unwatch <x y z>`: remove a watch.
- `/hearthbound perception_receipts`: emit status and bounded in-memory receipt history.

The first valid observation produces revision 1. Subsequent receipts are emitted only when observed wheat count/EMPTY/AVAILABLE state changes. Every receipt includes dimension, source coordinates, session-local revision, server tick, actual observed wheat count, marked citizen UUID, evidence origin and `action_authorized=false`. No agent or task controller consumes these receipts; they are read-only operator diagnostics. No chunks are loaded, source inventory is not mutated and no neural policy is promoted.

**Important restrictions:** Revisions are monitor-local and reset after server restart, unwatch/re-watch or monitor recreation. They are **not** resource transaction tokens, and cannot be used to authorize a haul. A change during chunk unload or beyond the observation cadence may not be witnessed; no claims of lossless event capture. This is a bounded **change-detection sampler**, not direct interception of all Forge inventory mutations or a distributed event bus. It requires one eligible marked Sable; otherwise the source is not sampled.

## Replay validation

`scripts/validate_live_perception_receipts.py` checks a saved receipt transcript for strict schema, dimension, source, UUID, revision sequence, monotonic tick, matching EMPTY/AVAILABLE wheat count and `action_authorized=false`. Run:

```sh
python3 scripts/validate_live_perception_receipts.py server-receipts.txt --output verified-perception.json
```

This tool parses only records actually present in the captured file; test fixtures are synthetic and are not claimed as real Minecraft events. Capture genuine operator command output from a dedicated server before producing a real-world report. The validator treats gaps/restarts as rejected streams; start a new file for a new watch session.

## Future machine-vision data alignment

The already added `hearthbound.vision-frame-manifest.v1` is a strict metadata contract, **not camera recording**. A separate Minecraft client or renderer process is needed to record true RGB frames, camera pose and server tick, then join those frames against these genuine observation receipts. The no-privileged-label-at-inference rule remains in force. For studies of emergence, compare CNN-from-scratch against explicitly labelled pretrained and structured-only controls using whole-world/layout held-outs.

## Validation gates

- Python read-only receipt parser and adversarial format tests.
- Full Forge compilation and dedicated-server smoke on this branch; compilation demonstrates compatibility, but does not prove the new command was exercised.
- **Still required:** real watch command, changing chest contents within Sable's range, observing a receipt with matching server tick, chunk-unload behavior, restart/reset behavior, client-side RGB capture alignment, and measured CPU/network cost.
- No new Minecraft gameplay autonomy, multi-citizen knowledge, network bridge, camera frames or neural learning claimed.

Follow-on milestone: add a controlled dedicated-server scenario invoking the new watch and receipts commands and export the actual log as an artifact. Then build the read-only cache adapter, with explicit permission-scoped citizen delivery, never conflating a sensor assertion with execution authority.
