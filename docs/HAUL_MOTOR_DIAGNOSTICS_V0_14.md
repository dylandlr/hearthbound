# Read-only haul and chunk diagnostics v0.14

Status: implementation and prospective validation contract. Live results belong
to the exact tested revision and retained CI artifacts. This change is stacked
on the private communication pilot in draft #216; the draft stack remains
unmerged.

## Why this is needed

The five-world reliability cohort at `d9485e20` retained one genuine physical
incompletion: three wheat at the destination, one active job, and one outstanding
source claim. The unfinished citizen was observed at integer block `(16,101,-1)`.
The fixture force-loads only block columns `(0,0)` through `(31,4)`, covering
chunks `(0,0)` and `(1,0)`. The citizen's last observed position is in chunk
`(1,-1)`, outside that forced region.

This is a testable lead, not an established historical cause. The old evidence
did not include entity-ticking eligibility, the citizen's tick counter, its
exact motor phase, or its retained cargo. A loaded entity can be visible to
inspection without receiving entity ticks; `SableHauling.active()` also includes
paused and quarantined jobs. Neither `loaded=true` nor `active_motor=true` proves
that the worker was walking or executing motor updates.

The [original run](https://github.com/dylandlr/hearthbound/actions/runs/45235844427)
and [summary](https://github.com/dylandlr/hearthbound/actions/runs/45235844427/artifacts/14850667131)
remain unchanged. The old outcome is not retroactively relabeled.

## Exact-subject operator command

```text
hearthbound-haul-diagnostics <canonical-citizen-UUID>
```

The permission-2 command inspects the requested loaded entity in the current
dimension. It never selects the nearest citizen. Its response begins with
`HAUL_MOTOR_DIAGNOSTICS_V1 ` and uses schema
`hearthbound.haul-motor-diagnostics.v1`.

| Evidence | Meaning |
| --- | --- |
| Citizen, existing world identity, dimension, game tick | Scope and chronology of this observation |
| Position, velocity, collision and ground flags | Precise movement state |
| Entity tick count, NoAI, Forge update permission | Separate entity advancement and update gates |
| Chunk coordinates, loaded/forced state, position entity-ticking eligibility | Distinguish presence from simulation eligibility |
| Typed haul fields, job, phase, error, source and destination | Preserve absent or malformed state without inventing defaults |
| Cargo tag, item and count | Retained native cargo, including malformed/unknown states |
| Existing source owner and claim-store presence | Owned, mismatched, unclaimed, or unavailable authority |
| Motor target, distance squared and reach threshold | Current eligibility for the physical interaction |
| Existing navigation target/path, next/end node and cursor | Current path state without asking the navigator to recompute it |
| Local loaded vanilla container inventory | Bounded endpoint observations with explicit coverage |

The motor checks distance to `(x+0.5,y+0.5,z+0.5)` with squared threshold `6.25`;
navigation requests `(x+0.5,y,z+0.5)`. Both geometries are reported. The diagnostic
does not alter either one.

Output is bounded to 3,900 UTF-8 bytes including the RCON newline. An oversized
snapshot returns an explicit unavailable response. It never emits truncated JSON
that could be mistaken for complete evidence. Missing UUIDs, unmarked entities,
unsupported inventories, unloaded endpoints, and unavailable stores remain
explicit. Inventory inspection is limited to local native Container NBT; it
does not resolve item capabilities, merge adjacent containers, or realize loot.

## Observation boundaries

The command executes on the Minecraft server thread. It never calls the motor,
requests or stops navigation, creates a path, acquires/releases a claim, repairs
an assignment, forces a chunk, or grants policy/reward authority. The additive
SavedData accessors inspect existing state without creating a world identity or
claim store. Existing data may be cached from disk.

Native entity serialization supplies the starting ForgeData snapshot. The
within-command invariant baseline begins **after that serialization** and covers
persistent ForgeData, path identity/index, claim snapshot, entity tick counter,
position, velocity, and NoAI. Those named checks describe the scope of
`strictly_read_only`; they do not certify all native or third-party serialization
hooks or an entire world state. A detected change produces an unusable
`OBSERVATION_SIDE_EFFECT_DETECTED` response.

Each successful citizen snapshot is a server-thread observation. A collection
of different citizens and later native commands is explicitly **not atomic**.
These operator observations are never fed into citizen memory or source menus.

## Original reliability trial remains the scoring contract

The existing four-citizen fixture, five seeds, force-loaded footprint, polling
window, physical success criteria, and accounting-event definitions remain
unchanged. New observations occur only after the original fixture outcome and
terminal scoring snapshot are fixed, before the runner's final disable/save.
The passing fixture may already have disabled dispatch itself.

The additional collector:

1. Retains the exact decision-trace response already requested by the unchanged
   original fixture. A valid complete trace supplies its four distinct citizen
   UUIDs without rediscovering identity by proximity. The four source-readiness
   queries remain current loaded-scope observations; they cannot silently replace
   that roster or introduce unrelated citizens. The retained command, RCON request
   ID, raw response, digest, and parsed citizen/job chronology remain inspectable.
   Trials without a retained complete trace use the explicitly bounded source-roster
   fallback and remain incomplete if four subjects are not established. An invalid
   retained trace remains an error even if the fallback finds four citizens.
2. Takes three rounds of exact-UUID snapshots, with one wall-clock second between
   rounds. Each snapshot supplies its actual server/entity tick counters.
3. In the first and last rounds, separately reads native job UUID, phase, and
   cargo. The exact UUID commands and recognized native values/absence responses
   remain in the artifact. Display names alone do not establish identity.
4. Writes `motor-diagnostics.json`, including the original terminal snapshot and
   its canonical SHA-256. The trial result records the diagnostic file's digest.
5. Preserves unavailable native replies and continues the remaining safe
   observations when a known subject disappears. `No entity was found` is
   unavailable state, never evidence of absent cargo. The strict coverage gate
   still requires all four subjects to be observed in every round, with valid
   native probes; missing or removed actors do not become complete evidence.
6. Reports sequence patterns without altering the original score or claiming a
   root cause. Natural completion during this phase remains a late diagnostic
   observation; it cannot turn the original failure into a pass.

The collector uses schema `hearthbound.colony-post-window-motor-diagnostics.v2`.
It records semantic snapshot and native-field failures individually and continues
the remaining subjects/rounds while the transport remains usable. A loaded
`OBSERVED` snapshot with `alive=false` is valid death evidence. A later missing
entity or unavailable native field still prevents complete coverage. Retaining
the original trace adds no command inside the original scoring window; validation
of that retained response begins only after the terminal score is frozen.
Artifact verification compares the entire retained trace set with the trial's
hashed original RCON log. Fallback identity requires that log to contain no
original trace command; deleting an invalid or additional trace cannot create
complete evidence.

Suspension is flagged only when world ticks advance across repeated observations,
the same citizen's tick counter remains unchanged, and its observed position is
ineligible for entity ticking throughout. Static counters without advancing world
time are insufficient. Unavailable claim ownership is distinct from an observed
different owner. A completed navigation path outside reach is a descriptive
pattern, not proof of why movement stopped.

The workflow passes `--require-motor-diagnostics` to the summarizer. Artifact
flags cannot disable this requirement. Missing/corrupt diagnostics fail their
separate coverage gate while preserving valid original accounting observations.
Invalid world/revision provenance prevents diagnostic findings from entering
aggregate counts. Every planned world remains present, and citizen-level patterns
are never counted as independent reliability trials.

## Controlled live acceptance

The new `real-haul-motor-diagnostics.yml` workflow predeclares one controlled
disposable-world trial before compilation and checks out the proposed head.

The first control reuses the existing sealed two-citizen hauling corridor and
its 75-by-two-second polling limits. A picks up one wheat while a barrier keeps
its destination beyond interaction reach; B completes independently. Repeated
diagnostic reads must preserve A's exact job, cargo, claim, and inventories,
corroborated by native entity/block NBT. Removing only the barrier must allow
that same job to deliver and release its claim. Missing, malformed, and unmarked
citizen identity probes must not silently select another worker.

The second control uses a fresh, unassigned NoAI probe at
`(4104.5,101,4088.5)`, with a forced neighboring anchor at `(4096,4096)`.
The probe has a predeclared UUID and is summoned with its Sable marker,
persistence, and NoAI already in its initial NBT. That UUID must differ from both
hauling workers and must not already be loaded. The fixture waits read-only for
that exact actor, within the declared 60-by-0.25-second readiness bound. Native
UUID, planned position/chunk, forced/entity-ticking state, and absence of a haul
must agree before any ticket is removed. There is no nearest-actor fallback or
post-spawn NoAI mutation. The original workers' NoAI and job/claim/inventory
authority are compared before and after the probe; their positions and navigation
can continue to change naturally.

Both chunks are loaded during setup. The operator then removes only the probe's
own chunk ticket. Each ticket intervention records and validates the exact native
success receipt for the expected chunk and dimension before proceeding. The test
requires the probe to remain loaded, ineligible for
entity ticking, and stationary with unchanged entity tick count across two
40-game-tick gaps. Restoring that chunk ticket once must make the same citizen
eligible and advance its tick count while NoAI remains set. The original hauling
workers are not moved or reassigned.

This controlled intervention validates the distinction between entity presence
and ticking. It does not establish why the historical #216 worker failed. The
fresh reliability cohort supplies separate observations of the original fixture.

The runner preserves first failures, secondary cleanup errors, plan, logs,
native world identity/seed, and file digests. It requires clean shutdown. There
are no behavioral retries or communication-performance winner gates.

## Retained first live attempt and fixture correction

At source `2b8c5a88048ca452eaa989bac793eb898f10aa05`, the
[first controlled run](https://github.com/dylandlr/hearthbound/actions/runs/45245168314)
passed actual Forge compilation, blocked-cargo inspection, independent B delivery,
same-job A recovery, and negative identity checks. It then failed during chunk
probe setup. The immediate unbounded nearest-Sable lookup after the distant
spawn returned completed B's UUID. The fixture set B's NoAI flag before its
fresh/unassigned check correctly rejected that actor.

The [original artifact](https://github.com/dylandlr/hearthbound/actions/runs/45245168314/artifacts/14853628303)
remains a failed overall acceptance, with SHA-256
`21ab85482f142846880fd6cf29f382c8a8470667c11ccb5b03bf66bd5244d62e`.
Its seven internal digests and native saved-world identity/seed verified.
Native inventory and job evidence establish the earlier two deliveries and
16-wheat conservation, but the later probe did modify an original worker.
There were no ticket-removal, suspension, or resume observations. The distant
actor's visibility/readiness was not established by the accepted spawn command.

The exact-UUID native-summon and readiness contract above corrects that fixture
error. It does not change the production motor, original four-citizen fixture,
physical acceptance thresholds, or chunk-suspension observation requirements.
Its new revision and fresh-world run remain separate from the failed first
attempt; a successful correction cannot overwrite that failure.

The same first revision's
[original reliability cohort](https://github.com/dylandlr/hearthbound/actions/runs/45245168165)
was independently verified as five passing worlds with complete diagnostics:
60 snapshots and 120 native field probes. One already-completed worker was
loaded but not entity-ticking; no active/carrying suspension was observed.
Both accounting-event definitions were 0/5, with a descriptive 95% Wilson
interval of 0–43.45%. The archived physical stall and historical accounting
issue therefore remain unresolved. Results from later revisions are not pooled
with this cohort.

At the next source revision, `3183e76fd43ab49844e59f65afefe875d4fac2a3`, the
[controlled run](https://github.com/dylandlr/hearthbound/actions/runs/45249680599)
verified the exact-UUID correction: eight readiness reads found no loaded probe,
then read nine identified the declared stationary, unassigned probe at its planned
position/chunk. Its separate native UUID witness matched, and both original
workers retained their NoAI and authority state. Minecraft then acknowledged
ticket removal with `Unmarked chunk [256, 255] in minecraft:overworld for force
loading`. The fixture incorrectly expected the add-command wording `force loaded`
and stopped before any suspension or resume reads. This second overall failure
is also retained, with [artifact 14857190333](https://github.com/dylandlr/hearthbound/actions/runs/45249680599/artifacts/14857190333)
and ZIP SHA-256 `17ffa36c0496cde131a2df253be194e73dee7821a30879c7e8a229c03d139a7e`.
The current ticket checks bind the actual successful native add/remove receipts
to the expected chunk and dimension.

That revision's [five-world reliability cohort](https://github.com/dylandlr/hearthbound/actions/runs/45249680629)
again had five passing original frozen scores, but only two complete diagnostic
captures. Worlds 02 and 05 saw only three nearby citizens during post-window
rediscovery, although their earlier original-fixture decision traces retained all
four UUIDs. World 03 recorded one completed, cargo-free worker alive at tick 162,
dead at tick 183, and not loaded at tick 203; the Forge log also records a fatal
fall. The subsequent native `No entity was found` response is unavailable evidence,
not an empty-cargo witness. This is separate from the archived active-haul stall.

The collector changes above retain the already-recorded identities and continue
partial observations without lowering coverage requirements or rescoring any
original outcome. The second cohort stays 5/5 original PASS with three incomplete
diagnostic captures; its failures are not overwritten by later observations.

## Validation and research connections

Focused offline commands:

```bash
python3 -m unittest discover -s scripts -p test_haul_motor_diagnostics.py -v
python3 -m unittest discover -s scripts -p test_colony_motor_diagnostics.py -v
python3 -m unittest discover -s scripts -p test_colony_reliability.py -v
gradle --no-daemon compileJava compileTestJava
```

Actual Forge compilation, the controlled live fixture, the five fresh reliability
worlds, and the existing applicable compatibility gates are required before
claiming live validation. Earlier and newer revisions remain separate cohorts.

The primary [research foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md) remains
Project Sid, MultiAgentBench, and MARBLE, with the PA4 readings. This work applies
their architectural/evaluation lessons through explicit action ownership,
attributable observations, separate physical and accounting outcomes, and complete
failure records. In particular, PA4 P06/P07 motivate inspectable failure modes,
P37 distinguishes observation from executed action, and P32/P33 motivate cautious
world-level empirical estimates. This diagnostic work does not introduce a learned
policy, an LLM controller, a new coordination topology, or societal emergence.
