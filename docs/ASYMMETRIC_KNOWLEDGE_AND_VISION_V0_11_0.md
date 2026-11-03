# Hearthbound v0.11.0 — Asymmetric citizen knowledge, delayed communication and visual-frame provenance

## Change in research question

v0.10.9 introduced versioned, permission-scoped colony events and a cache of citizen beliefs. Its optional citizen-to-citizen sharing added **no measured benefit** because all citizens already received the same source updates. That benchmark was a reference simulator, not an actual Forge event bridge.

In this milestone, *three scouts* can inspect different sources, while *six workers* cannot read those sources directly. Every worker must receive a permitted scout report before attempting a haul. The underlying server remains authoritative: an action must match the actual source's current version and stock.

## Implemented simulated communication model

- Scout observations are scoped to one assigned local source; workers have no privileged inventory-reading API.
- A peer transport permits only registered scout objects to speak about their assigned source, and only to workers granted that source. The model intentionally does **not** claim cryptographic identity verification.
- Messages carry source, observed value, source revision, original observation tick, sender, recipient and scheduled delivery tick.
- The receiver preserves timestamps and versions, rejects older revisions and stops presenting a source as currently known after its TTL expires.
- Transport profiles compare ideal, two-step delayed, seeded 25% loss, and seeded approximately 33% loss plus three-step delay.
- Outcomes distinguish actual committed simulated hauls from failed requests based on stale reports, and explicitly count local scout inspections, transmissions, drops and deliveries.

A fixed resource-production schedule and matched episode seed make comparison reproducible. The **no-messages** baseline is deliberately incapable of remote hauling, because workers have no local visibility or alternative discovery path in this small simulation. It is an isolation test demonstrating a communication channel's effect, not a realistic head-to-head contest against a complete independent colony policy.

## Future machine vision capture contract

The separate `hearthbound.vision-frame-manifest.v1` validation module requires frame ID, server tick, world seed, layout identity, camera pose, resolution, image checksum, and train/validation/test split. The split is assigned by a **world-seed plus layout** identity, not by adjacent video frames, to prevent the same scene leaking across training and testing.

A record cannot claim a captured frame without actual nonempty image bytes. Training-only authoritative structured labels must never enter a visual-only policy's inference input. The contract records zero collected frames and zero trained visual models. Future phases can use a real first-person Minecraft render capture or a spectator-attached camera, but must distinguish the two observation privileges.

Recommended experiment when capture exists: small CNN-based encoders from scratch against an explicitly labeled pretrained-vision control; evaluate actual distant objects, occlusions, lighting, texture changes, Create machines and unseen world layouts. Add GRU/recurrent memory only after basic frame/state alignment, visibility masks and source-frame provenance have been validated. Visual hypotheses remain non-authoritative for inventory and task execution.

## Safety and integration scope

This PR adds a **Python simulator and a manifest validation contract**, not a Forge runtime bus, camera capture service, gameplay messages, or neural deployment. No additional LLMs, pretrained world knowledge or actual Minecraft agent decisions are introduced. The latest v0.10.9 Forge, dedicated-server and Java checks passed; they do not prove the new asymmetric communication model works inside Minecraft.

Next implementation phase: add read-only Forge event receipts with source version, server tick, receiver visibility, job correlation IDs and chunk lifecycle boundaries. For real social systems, allow local scouts to share observations and test lost/out-of-order messages, uncertainty and cooperation with multiple independent worker objectives.

## Completed first CI results — November 3, 2026

The standalone [run 41728495628](https://github.com/dylandlr/hearthbound/actions/runs/41728495628) passed permissions, revision ordering, stale-message rejection, source-authoritative task checks, frame-manifest validation and the four-seed simulated comparison.

Every run uses 150 abstract ticks and **exactly 30 synthetic production events**, with three local scouts and six remote workers. Under the deliberately restrictive baseline, remote workers cannot inspect any stock and receive no messages.

| Synthetic transport | No-message remote hauls | Shared-message remote hauls | Delivered messages per run | Denied stale haul attempts per run |
|---|---:|---:|---:|---:|
| Ideal, no delay | 0 | 30 | 2,700 | 30 |
| Two-step delay | 0 | 30 | 2,664 | 150 |
| Seeded lossy delivery | 0 | 30 | 2,007–2,047 | 93–101 |
| Three-step delay + loss | 0 | 30 | 1,747–1,771 | 213–221 |

**Interpretation:** In this toy environment, information exchange lets workers successfully act on remote sources they cannot inspect. That result follows partly from the artificial no-message restriction, so it cannot establish a causal advantage against a realistic colony without alternative exploration, navigation or autonomous source inspection. Delayed messages substantially increase stale, rejected proposals; the authoritative stock/revision check prevents them from executing. The system broadcasts scout facts every tick to every worker (up to 2,700 delivered messages), making this an **intentionally inefficient communication baseline**. The next test should compare source-change-only messaging, subscriptions, on-demand requests, aggregation and worker coordination rather than assume frequent broadcasts are desirable.

Machine vision remains a **validated data-contract proposal only**: the test uses placeholder bytes solely to exercise frame-record validation; no real Minecraft frames were captured and no visual model was trained.

### New next milestone

Implement a read-only Forge receipt emitter for inventory/job changes, with source revisions and server ticks, and a client/agent observation adapter that consumes events without modifying the task-authority layer. Compare the emitted Minecraft event traces against ground-truth inventory snapshots. Separately capture synchronized client RGB frames on actual gameplay runs, with whole-world layout holdouts before training any CNN.
