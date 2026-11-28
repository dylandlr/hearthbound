# Post-delivery citizen death: retained native failure

Recorded 27 November 2026 (America/Chicago). Follow-up:
[QA #353](https://github.com/dylandlr/hearthbound/issues/353), under baseline integration
[C00-02 / #227](https://github.com/dylandlr/hearthbound/issues/227).

**The required diagnostic gate failed after verified material completion.** This is a retained native
failure discovered while validating draft PR349. Its cause is not attributed to that change. The
successful wheat transfers do not turn this diagnostic failure into a successful acceptance run.

## Source and artifact

| Field | Evidence |
| --- | --- |
| Source head | `64c0fc63cb1940928c0b9abb53763f75abf7f1db` |
| Source tree | `5917af6e5df072b37b9281c6e3ffab17035f2fa3` |
| Run / attempt | [46096030716](https://github.com/dylandlr/hearthbound/actions/runs/46096030716) / 1 |
| Failed world job | [140827445614](https://github.com/dylandlr/hearthbound/actions/runs/46096030716/job/140827445614) |
| Trial / seed | world-02 / 43102 |
| World UUID | `02a5a741-8630-4b9e-ac29-92830243e2e2` |
| Citizen UUID | `16d1e8b4-76b6-42e1-abbc-d4c2eda0826c` |
| Artifact | [15243508369](https://github.com/dylandlr/hearthbound/actions/runs/46096030716/artifacts/15243508369), 246,031 bytes |
| Verified ZIP SHA-256 | `c77b5907b1b836b42aebcc6888f74782d8d781f95ff32f67825e3fe660b8cc22` |

The archive size, digest and source head match GitHub metadata. Internal diagnostic, RCON and
server-log hashes were checked. The [retained diagnosis](evidence/civilization100/citizen-lifecycle-failure.json)
contains all eleven subject request/response exchanges, exact source files and the distinctions
between observations, inference and unestablished cause.

## Observation sequence

Before diagnostic sampling, the terminal read-only snapshot reported four physically completed
transfers, exactly four wheat at the destination, all four source inventories empty, no outstanding
claims and four completed citizens loaded. The archived fixture result was `PASS`.

The planned three diagnostic rounds then observed the same exact UUID:

| Request | Native tick | Observed state |
| --- | ---: | --- |
| 67 | 139 | Alive and airborne at y=82.68393, vertical velocity −1.45688; job COMPLETE, delivered tick 113 |
| 91 | 160 | `alive=false`, position approximately (14.99793549, 71, −1.33240373) |
| 95 | 180 | `NOT_LOADED_IN_DIMENSION` |
| 96–98 | Subsequent queries in that sample | No entity found for the native job, phase and cargo queries |

At ticks 139 and 160 the relevant chunk [0,−1] was loaded and entity-ticking, but not force-loaded.
There is no chunk observation for the absent tick-180 sample. The native alive flag directly
establishes death of this UUID; absence alone would not distinguish death from unloading.

The server log at 02:10:12 UTC reports a Sable fall death at the matching rounded position. Its
numeric runtime entity ID is 388. An explicit numeric-ID-to-UUID mapping was not retained, so that
particular log association is an inference from matching name and position. The preceding exact-UUID
dead observation is independent of that inference.

The fixture created an elevated stone platform at x=0–31, y=99, z=0–4 and force-loaded the platform's
chunks. The observed falling citizen was outside that z interval. These geometry facts do not
establish why it left the platform or which controlling behavior initiated the motion.

## Bounded source review after the failure

The failed citizen's native job was already COMPLETE at tick 139, with no cargo or source claim.
Its diagnostic snapshot reports `no_ai=false`, no active navigation path, navigation `done=true`,
and a retained navigation target of (17,100,1). The destination was (16,100,1). These fields do not
identify the movement that originally took it beyond the platform.

At the published source, `SableHauling.tick` returns for COMPLETE and its successful insertion path
records delivery, releases the source claim and reconciles the owned colony task. It does not stop
navigation, zero velocity or disable vanilla AI at that boundary. `SableController.onLivingTick`
performs its ordinary Sable motor/idle decisions on a 20-entity-tick cadence; its no-nearby-player
fallback stops navigation on an idle cycle. Those production movement/settlement statements are
unchanged from the baseline. The PR349 diff adds assignment/insertion observations and the inspection
command; `HaulMotorDiagnostics.inventory` changes visibility only.

This establishes relevant existing behavior and limits the source delta. It does not show that a
remaining path, vanilla AI, collision, momentum or observation timing caused this fall. At the first
archived post-window sample the path is already absent. A justified follow-up needs the exact UUID's
position/velocity/support and action-owner/navigation state at the insertion boundary and through the
departure, with life-state transitions retained. It must preserve ordinary physics and the unchanged
acceptance windows rather than freezing a citizen until the observer has finished.

## Acceptance and investigation boundary

The collector retained all three rounds and reported `INCOMPLETE`; the world process exited 1.
Four sibling world jobs passed. The full five-world
[summary job](https://github.com/dylandlr/hearthbound/actions/runs/46096030716/job/140830687253)
also failed. Material completion, later life state and diagnostic coverage remain separate facts.

There are no per-request wall-clock timestamps in the raw RCON log. Request IDs and observed native
ticks establish order; the recorded planned wall interval is one second. No samples after the final
three native presence queries were taken. The record does not establish a longer absence duration,
the reason for leaving the platform, or a causal relationship to the arrival-witness patch.

QA353 requires source-pinned action/geometry investigation, lifecycle-aware diagnostic semantics,
focused alive→dead→absent and duplicate-name tests, and a bounded native comparison if a justified
correction is implemented. The existing failed trial stays in its cohort. No radius increase,
teleportation, gravity removal, opportunistic freeze, force-loading or shortened observation window
was used to hide the failure. No workflow was rerun.

The applicable reference principles are stable identity, independently observed outcomes and
complete trial accounting. The physical findings here come from the native archive. They do not
demonstrate a learning effect, reliable long-term survival, 100-citizen operation or job specialization.
