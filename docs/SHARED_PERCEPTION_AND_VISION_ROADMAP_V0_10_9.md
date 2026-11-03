# Hearthbound v0.10.9 — Event-driven shared colony perception

## Outcome and scope

This milestone introduces a small, independently testable **Java 17 shared perception ledger** in `dev.hearthbound.perception`. It is a foundation for Forge event adapters and future machine vision, **not yet wired to a running Minecraft world**. It performs no hidden server scans, reads no inventories, grants no task authority, and sends no controls to agents.

The v0.10.8 adaptive sensing experiment established that scalar observation penalties alone did not create an attractive productivity/refresh tradeoff. Here we change the mechanism instead: changes at observed objects can enter a bounded event channel, and only subscribed citizens receive the update.

## Core design

- **Event subjects**: opaque names or identifiers such as a mill or chest; an integration adapter will later map them to validated Minecraft block entities, world/dimension, and observation scope.
- **Scoped subscriptions**: subscribe/unsubscribe per citizen and subject; this prototype makes no authorization decision. A future Forge adapter must check proximity, jobs, permissions, and information-sharing policy **before** subscribing.
- **Provenance**: `SERVER_EVENT`, `DIRECT_OBSERVATION`, `CITIZEN_REPORT`, and `VISION_PREDICTION`. Unverified hearsay/visual predictions may add information but cannot overwrite already-held authoritative facts. This is a data rule, not cryptographic origin authentication; producers must be authenticated by their adapter.
- **Aging**: each fact includes observed world tick, sequence and bounded validity lifetime. Reads return `CURRENT`, `EXPIRED`, `GAP` or `UNKNOWN`; stale cache entries are never silently presented as current.
- **Backpressure**: per-citizen inboxes are bounded. Overflow emits a visible gap receipt on drain and invalidates cached facts before applying retained updates. The system must later support subject-specific bounded resync rather than assuming no events were missed.
- **Independent scopes**: a citizen with no subscription cannot read another citizen's cached subject.
- **Non-authoritative learning boundary**: the ledger provides evidence to policy observations; it does **not** authorize hauling or override server-side task claims. Actual interaction must still validate current inventory, position, permissions and task ownership.

### Planned game integration

Connect adapters to Minecraft/Forge block-entity dirty/change events, Create machine status, job-completion ledger events, citizen-owned inventory updates and nearby-entity observation. Publish an event only if the source and intended recipient have a justified observation path. A citizen physically seeing a machine may receive a directly observed fact; a distant citizen could receive a *reported* fact if a courier, messenger, notice board or permitted colony network delivered it. Do not automatically broadcast every world's block state to every agent.

Add snapshot+delta recovery with clear dimensions, object identity, epoch/version, event-tick and causal identity. Record server tick and matching task ledger event IDs. Add rate/cost profiling only after this is running on Forge; any claimed savings before then are synthetic.

## Future machine-vision perception

We should support **egocentric machine vision** as an optional observation modality, not force it into the first structured-state simulator. A proposed v1 camera branch:

1. **Visible-frame input**: RGB image from the agent's actual camera at a fixed resolution and FOV; optional camera pose and depth only if directly observable or explicitly supplied for an ablation. No globally indexed inventory/block-coordinate oracle in the visual input.
2. **Learned encoding**: compare a lightweight CNN (spatial features) against a compact visual transformer / pretrained-free visual encoder, with temporal frame stacking or GRU for partial observability. Start with cheap lower-resolution inputs; profile real-time throughput before selecting architecture.
3. **Grounded candidate facts**: perceivable objects, relative bearings, motion, open/closed appearance and uncertainty; represent them as `VISION_PREDICTION` with confidence, frame ID, observation tick, spatial scope and model-checkpoint hash in an extended envelope. An unseen chest's actual contents **cannot** be inferred as a verified fact from pixels.
4. **Memory fusion**: camera predictions enter the same evidence ledger beside direct interactions and citizen reports, but remain non-authoritative. The policy may choose to inspect an object for confirmation; the supervisor never executes task requests solely because a vision guess said it contained wheat.
5. **Training/evaluation**: hold out world seeds, biome/lighting/weather/texture packs, camera offsets, skin/entity occlusions, and time gaps. Compare structured-only, vision-only and fused observation variants. Use server knowledge for evaluator ground truth, never as invisible input to a visual agent. Track localization accuracy, uncertainty calibration, frame latency, collision outcomes, and downstream task success.

This is a design for **future work**, not a trained vision model or a working camera render pipeline today. The immediate goal is to establish a trustworthy representation contract that both non-visual and visual perception can ultimately feed.

## Acceptance and limitations

A dedicated Java 17 CI workflow compiles the ledger without Forge and tests subscription isolation, event delivery, TTL expiration, known/unknown states, hearsay not overriding an authoritative fact, observable queue overflow and invalid inputs. This is real code tested independently, **but not yet a real-world Forge event bridge**. Dedicated-server smoke is separately required after adapters are introduced, followed by measuring actual tick-time, allocations, event volume, dropped subscriptions, and citizen action outcomes.

No LLMs, no live neural policy promotion, no agent camera API, and no claim of vision-based Minecraft learning are included in v0.10.9.
