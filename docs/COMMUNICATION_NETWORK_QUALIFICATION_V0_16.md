# Six-arm communication runtime qualification v0.16

## Purpose and boundary

This change implements and adds qualification for the four additional communication
conditions predeclared in [the frozen v1 study](COMMUNICATION_EXPERIMENT_PREREGISTRATION_V1.md):
DIRECT_UNREAD, STAR, CHAIN, and CYCLE. NO_MESSAGES and DIRECT provide engineering
controls. All six use the existing scripted private-source policy and native
Minecraft hauling executor. The production colony dispatcher remains outside
this opt-in experiment.

The inspected base is `74763d7cc0b0c7e8f04d8af79ed4120ca5fbcf9f`, the final
PR #218 source. Its successful cold builds, original reliability cohort,
private pilot, and controlled diagnostics are evidence for that source. A new
source revision gets separate first outcomes; earlier results are not inherited
as proof that this implementation works.

The 144-world design, its manifest, generator, validator, and tests remain
unchanged. Its canonical design digest is
`43588a883e3c5674deff44e022ca9c4819d5e1ca48c82b664884ff603fdc6b45`.
The original preregistration's implementation-status text records its baseline;
this document describes the subsequent qualification work.

**This is engineering qualification, not execution of the 144-world study.**
The offline execution guard remains closed. The new runtime command also
refuses actual generated world seeds 55101 through 55124. A later study needs
the separately reviewed execution binding, dependency and artifact identities,
complete analysis/reporting, and exact-revision capability evidence required by
the preregistration. Qualification results alone do not authorize that launch.

Learned collaboration, LLM control, strategic equilibria, and societal emergence
remain future experimental targets.

## Runtime contract

`CommunicationNetworkPolicy` defines the following undirected logical-slot
permissions. Actual transport remains one-hop, range limited, provenance
checked, and restricted to the sender's own direct observations.

| Arm | Permission edges | Reports exposed to decisions |
| --- | --- | --- |
| NO_MESSAGES | None | No |
| DIRECT | All six pairs | Yes |
| DIRECT_UNREAD | All six pairs | No |
| STAR | 0–1, 0–2, 0–3 | Yes |
| CHAIN | 0–1, 1–2, 2–3 | Yes |
| CYCLE | 0–1, 1–2, 2–3, 3–0 | Yes |

The legacy `configure` command remains restricted to NO_MESSAGES and DIRECT.
Its v1 schema, response prefix, fixture, clock, policy, and export semantics
remain intact. The separate `configure-network` command uses
`hearthbound.communication-network-trial.v1` and
`COMMUNICATION_NETWORK_TRIAL_V1` exports. It requires an explicit permutation
mapping logical slots to physical seats, bounded trial/block identities, the
600-tick horizon, and the declared overworld destination.

Enrollment verifies each actor is frozen at the exact position of its declared
physical seat. Actors retain separate private memories and inboxes. A star hub
does not gain a coordinator role or global state; a chain does not gain relaying.

Every sender proposes the existing rotating recipient
`(sender_slot + 1 + round % 3) % 4`. If a fresh own observation is available,
the send budget is charged before permission and transport checks. A blocked
edge records `TOPOLOGY_BLOCKED`; the sender does not try another peer. With no
eligible observation, an explicit `SEND_OPPORTUNITY` record reports
`NO_ELIGIBLE_DIRECT_EVIDENCE` and charges zero sends. Thus all 120 opportunities
in a complete 30-round world are accounted for.

Each attempted send binds its exact journal attempt ID, source observation and
revision, sender/recipient identities, logical slots, physical seats, round,
permission edge, edge decision, and direct recipient route. A proposed or
rejected route is not presented as a completed delivery. The existing public
transport method retains its response strings and performs one send; an
additive internal receipt exposes that same attempt identity to the new mode.

DIRECT_UNREAD performs normal truthful transport and retains delivery costs,
inboxes, and durable communication history. The policy does not invoke its
report supplier, admit received reports into its candidate menu, emit policy
READ/SELECTED events, or create report-cued assignments. Operator evidence
inspection is separate from policy consumption.

Fresh direct rechecks remain required before assignment. A sent, delivered,
read, or selected report does not earn physical completion credit. Native
hauling, claims, pickup, insertion, and conservation rules are unchanged.

## Prospective six-world engineering cohort

The new plan writer declares these slots before dependency setup:

| Slot | Arm | Generated world seed | Policy seed |
| --- | --- | --- | --- |
| qual-no-messages | NO_MESSAGES | 56101 | 66104 |
| qual-direct | DIRECT | 56101 | 66104 |
| qual-direct-unread | DIRECT_UNREAD | 56101 | 66104 |
| qual-star | STAR | 56101 | 66104 |
| qual-chain | CHAIN | 56101 | 66104 |
| qual-cycle | CYCLE | 56101 | 66104 |

Every slot uses a new JVM, empty world directory, unique persisted world/session
identities, and empty agent state. Actor UUIDs use a qualification-specific
namespace. Logical slots map to physical seats `[2,0,3,1]`; this nonidentity
permutation exercises role/seat separation. It is not the expanded study's
24-permutation counterbalance.

The fixture retains four workers, two sources containing two wheat each, the
shared empty destination, common sensing and action budgets, 30 rounds at
ticks 0 through 580, and the final freeze at tick 600. There is no early stop
after four deliveries, outcome quota, required contribution by every actor,
required report-cued completion, or required communication advantage.

GitHub may schedule at most two qualification jobs concurrently. Their actual
job order and hardware timing are uncontrolled. This choice is declared before
results and is unsuitable for matched-compute or performance-effect claims.
The expanded study's serial schedule remains unchanged.

Each slot permits one dependency-setup attempt and one world attempt. The
runner requires a matching successful first-build record before creating a
world and reserves its attempt before runtime work. Existing attempt records
cannot be overwritten. Failed setup leaves performance unknown. Missing,
incomplete, and invalid artifacts remain explicit rows in the six-slot summary.
There are no replacement worlds, changed seeds, or manual workflow reruns.
A correction requires a new immutable source and separate cohort.

## Validity and capability coverage are separate

A world may be a valid fixed-horizon observation with zero output or no
deliveries. Such an observation does not necessarily exercise the intended
communication mechanism. The following live coverage conditions are declared
before the first run:

| Arm | Minimum mechanism evidence |
| --- | --- |
| NO_MESSAGES | At least one network-disabled send; no deliveries or policy use |
| DIRECT | At least one actual truthful delivery |
| DIRECT_UNREAD | At least one actual truthful delivery; zero policy READ, SELECTED, or report-cued jobs |
| STAR, CHAIN, CYCLE | At least one topology-blocked proposal and one allowed transport attempt |

Missing coverage is `NOT_EXERCISED`, even when the physical observation is valid.
It cannot grant a future capability or trigger a replacement trial. Pure Java
contracts check all directed slot pairs, both directions of each edge, recipient
rotation, charged blocked attempts, access isolation, all seat permutations,
and the closed legacy interface. A six-world live sample is not assumed to
exercise every directed edge or every transport rejection category.

The qualification summary reports validity, coverage, actual events, costs,
and physical outcomes for all six slots. It does not calculate a population
effect, declare a winning network, pool earlier pilots, or estimate the original
production task-board accounting failure rate.

## Independent evidence and lifecycle checks

The collector preserves raw RCON responses, configuration, initial state,
fixed-horizon exports, repeated frozen-state witnesses, actor/native job and
cargo fields, inventories, source knowledge, inboxes, and persisted communication
SavedData. The plan/result bind the exact source commit/tree, protocol digest,
workflow attempt, qualification manifest, and build inputs. Saved `level.dat`
and world-identity NBT establish the actual generated seed and world identity.
An evidence ledger hashes retained files.

The independent validator checks runtime send opportunities against journal
attempts, permissions, ownership, observation revisions, and exact recipients.
It keeps send, delivery, READ, SELECTED, fresh recheck, assignment, and physical
completion distinct. Historical completed jobs may be overwritten in a
citizen's final current-job field; their durable histories and original physical
witnesses remain necessary.

Native inbox evidence is checked against actual delivery history and the
transport's pruning order. Duplicate detection occurs before pruning; expiry
alone does not physically remove an entry until a subsequent new delivery.
FIFO eviction, expiry, never-read, and never-selected categories can overlap.
Operator inbox reads do not create policy READ events. Malformed or unavailable
native data cannot become an empty-inbox assertion.

Any overflow, missing mandatory evidence, invalid identity, changed frozen
state, or conservation violation prevents protocol qualification. Raw failures
remain retained rather than clipped into valid outcomes.

## Original reliability and compatibility

The original five-world reliability cohort retains seeds 43101–43105, its
untouched four-citizen fixture, observation window, task-accounting definitions,
and strict three-round diagnostic coverage. New qualification worlds do not
enter that cohort. Original scores are frozen before diagnostic collection;
there are no actor repairs, altered forced footprints, or rescoring to obtain
a pass. Unknown/unloaded native probes are not empty cargo.

The legacy six-world private pilot and controlled haul/chunk diagnostic also
remain separate. Their workflows, Forge cold compilation, transport/restart
acceptance, and existing Minecraft compatibility gates run on the new source.
The legacy private protocol's only Python change is adding the new policy
dependency to its fingerprint. Its runner and scoring functions are unchanged.

The earlier active-carrying stall, accounting issue, setup failures, and
incomplete diagnostic capture remain unresolved evidence in PR #218. Successful
qualification cannot retroactively establish their causes.

## Research references and implementation status

[Project Sid, MultiAgentBench/MARBLE, and the selected PA4 readings](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md)
remain the primary foundation. This implementation translates their
information-flow, failure-visibility, and evaluation questions into explicit
transport permissions, access controls, and physical evidence. It does not
reproduce their LLM protocols or claim social emergence.

Implementation and local contract results must be distinguished from live
qualification. Actual first outcomes, source revisions, archive identities,
and independent replay findings are recorded in the accompanying draft PR.
No live result is asserted by this prospective document.
