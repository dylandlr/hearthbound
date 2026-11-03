# Hearthbound v0.10.9 — Event-driven colony knowledge and machine-vision roadmap

## Why this milestone

The v0.10.8 simulator results show that increasing a simple sensor-refresh cost does not reliably reduce sensing while preserving flour production. A low cost preserved 95.00% simulated success but caused **5,028** refreshes versus **5,010** for the legacy policy; a larger penalty cut refreshes to **3,359** but dropped success to **74.48%**. We should reduce redundant queries by changing **how facts reach citizens**, rather than forcing arbitrary information quotas.

## Immediate implemented experiment

`scripts/simulate_colony_perception_bus.py` adds three strictly separated roles:

1. **World authority:** commits a versioned state change and grants a simulated haul only when the source is still AVAILABLE **at the expected version**. An event/belief alone cannot execute a job. The real Forge execution gate is unchanged.
2. **Permissioned event bus:** delivers `INVENTORY_CHANGED`, `MACHINE_CHANGED`, or `JOB_COMPLETED` only to explicitly subscribed and visibility-permitted receivers. This standalone model trusts its in-process server event source; an actor string is **not** a cryptographic signature and must not be treated as proof of authenticity over network transport.
3. **Citizen knowledge:** tracks source value, version, observed tick, received tick, provenance (LOCAL, SHARED, or VISUAL_HYPOTHESIS), observer and bounded TTL. Rejects older revisions, ignores undisclosed sources and exposes stale cached values as UNKNOWN-to-decision rather than presenting historical inventory as a current fact. Sharing is optional and permission-scoped.

Comparison arms in the **fast synthetic simulator only**: every citizen polls all three sources each tick, subscribers receive authoritative events, or subscribers additionally exchange bounded shared facts. The benchmark counts inspections and deliveries, simulated hauls and denied task commits. It is **not** a Minecraft server-performance benchmark; in this simulator subscribers have reliable immediate delivery and the API has no network latency, chunk boundaries or concurrency races.

No new neural model is trained in v0.10.9. This is an experimental perception *infrastructure contract* for later ML observations, not an inference-performance claim.

## Future: machine vision as another observation modality

The intended progression is **structured Minecraft perception → optional rendered vision → multimodal learned perception**, while keeping server-side task authorization independent of both.

| Phase | Agent observation | Research question | Evidence needed |
|---|---|---|---|
| V0: authoritative structured state | Bounded nearby block/entity/task facts and versioned events | Can partial observation, event subscriptions and shared memories support useful plans? | Real Forge instrumentation, event timing, stale-state rejection and CPU overhead |
| V1: visual observation pipeline | Timestamped first-person or agent-facing RGB frame, camera pose, valid chunk status and matched event IDs | Can a small vision encoder detect wheat, villagers, tools, paths and Create machines without privileged labels at inference? | Paired frame→structured scene annotations, train/validation world splits |
| V2: visual-only control baseline | Embeddings from a CNN or lightweight ViT, proprioception and action history | Does machine vision generalize across texture packs, lighting, weather, occlusion and unfamiliar builds? | Held-out world seeds, lighting/texture shifts, missed detection rates, navigation outcomes |
| V3: multimodal learned state | Visual embeddings + permitted local state + received information events | When should a citizen trust sight, memory, or another worker's report? | Calibrated uncertainty, stale knowledge and conflicting sensor tests |
| V4: research comparison | Visual-only vs structured-only vs fusion vs scripted vs non-LLM RL | Are representations helping with emergent discovery, or just copying structured sensor answers? | Equal task/action privileges, held-out tests, instrumented real world results |

**Key design constraint:** a `VISUAL_HYPOTHESIS` can support tentative plans but cannot satisfy an authoritative inventory/ownership predicate. Even a high-confidence neural perception classifier does not turn a cached camera frame into an execution-time resource grant.

### Suggested vision model direction

Start with a compact CNN encoder or pretrained-for-representation visual backbone evaluated with frozen features, then train a temporal GRU or attention-based history aggregator if the tests show it is useful. For experiments aimed at knowledge emerging from gameplay, train visual encoders and policies from scratch or explicitly label externally pretrained vision models as a **separate baseline**, not a knowledge-free agent. Do not mix visual-only and Mineflayer/Forge privileged observations without reporting the difference.

Capture paired camera frames and authoritative *training-only* labels at the same server tick. Split by **entire world seed and build layout**, not adjacent video frames, to avoid temporal leakage. Evaluate precision/recall and calibration by entity or machine category and count visible-but-unreachable false positives. Run RGB input at a bounded cadence; use event streams to trigger expensive reinspection when needed, and instrument real CPU/memory/network usage rather than assuming an image input is always cheaper.

## Next real Minecraft work

Add a read-only Forge source-event bridge producing `hearthbound.colony-perception-event.v1` receipts, explicit subscriber ACL and per-citizen cache, plus source-side sequence numbers and total-order handling after chunk unload/reload. Instrument actual inspection counts and event latencies, compare against polling, and collect camera frame/event alignment metadata. Keep strict limits on receiver visibility and preserve independent authority for every physical task.

Current PR is only a Python reference simulator and test suite. No new gameplay, vision inference, model deployment or Minecraft world was executed by this benchmark.

## Completed standalone CI findings — November 3, 2026

[GitHub Actions run 41722852327](https://github.com/dylandlr/hearthbound/actions/runs/41722852327) passed version/TTL/visibility and simulated task-authority tests plus the four-seed comparison. Each run simulated 12 citizens, 3 inventory sources and 140 world steps:

| Arm | Synthetic source inspections per run | Event deliveries per run | Simulated successful hauls, seeds 11/13/17/19 |
|---|---:|---:|---|
| Poll every source, every citizen, every tick | **5,040** | 0 | 16 / 16 / 16 / 16 |
| Event subscriptions | **0** | 408–420 | 15 / 16 / 15 / 15 |
| Event subscriptions + shared facts | **0** | 408–420 | 15 / 16 / 15 / 15 |

The results confirm the reference implementation behaves as designed. They **do not establish actual CPU reductions**, because the abstract bus models reliable zero-latency delivery and has no measured Forge inventory cost. Nor do they demonstrate improved colony knowledge from citizen communication: all subscribers already receive the same trusted events, so sharing redundant facts adds nothing. A practical next experiment must introduce uneven local visibility, delivery delay/drops, and structured citizen messaging to establish incremental value.

The 15-versus-16 simulated-haul difference in some seeds further cautions against describing event delivery as automatically better for productivity. All real physical job control remains outside this experimental event bus.

The vision path remains a documented design proposal only: no frames collected, CNN trained or visual-only agents tested in this milestone.
