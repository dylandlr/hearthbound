# Communication experiment v1: offline preregistration

**Status: design frozen; expanded runtime unavailable; execution blocked.**
This document and [the exact machine-readable design](experiments/communication-v1.design.json)
predeclare a larger study. They do not implement the new runtime arms, dispatch
worlds, or report new performance results. The generator and validator are
[`scripts/communication_preregistration.py`](../scripts/communication_preregistration.py).
The original [six-world pilot](PRIVATE_COMMUNICATION_PILOT_V0_13.md), its runner,
its scorer, and its Java controller remain unchanged.

The inspected baseline is `31febdd08223b5575a09da14a51b3a036726ceb9`.
It supports only `NO_MESSAGES` and `DIRECT`. That commit is context, **not** an
execution binding for this expanded design. Learned collaboration, LLM control,
strategic equilibria, and societal emergence remain future experimental targets.

## Question and prior evidence

Within the existing four-worker hauling fixture, how do permission to exchange
source information, policy access to delivered information, and restrictions on
the communication graph change independently verified physical output?

The preceding pilot planned six worlds in three seed pairs. Five worlds were
valid, two pairs were complete, and their DIRECT minus NO_MESSAGES destination
gains were `[1, 0]`. One planned isolated world failed dependency setup before
runtime. That failure remains in the six-world denominator. These results
motivate this prospective design; they are not pooled into it, used as a power
calculation, or treated as evidence that communication always helps. The pilot
did not match native entity RNG or establish identical full world state.

This study also remains separate from the original production-dispatch
three-of-four accounting and active-haul reliability cohorts. Its private
controller bypasses the production task board. Success here cannot resolve
those original failures.

## Six arms with precise semantics

Graph vertices are **logical citizen slots 0–3**. An undirected permission edge
allows both directions. Every actual delivery still requires the existing
same-dimension and 12-block distance checks, valid provenance, fresh direct
evidence, and a valid recipient inbox. A connected permission graph does not
guarantee a connected realized delivery graph.

| Arm | Undirected permission edges | Report access in decisions | Baseline support |
| --- | --- | --- | --- |
| `NO_MESSAGES` | None | None; send attempts recorded as `NETWORK_DISABLED` | Existing pilot arm |
| `DIRECT` | 0–1, 0–2, 0–3, 1–2, 1–3, 2–3 | Existing bounded private report access | Existing pilot arm |
| `DIRECT_UNREAD` | Same six edges as DIRECT | Truthful deliveries persist in the inbox and audit, but no policy READ, SELECTED, or report-cued assignment | Requires implementation |
| `STAR` | 0–1, 0–2, 0–3 | Same as DIRECT | Requires implementation |
| `CHAIN` | 0–1, 1–2, 2–3 | Same as DIRECT | Requires implementation |
| `CYCLE` | 0–1, 1–2, 2–3, 3–0 | Same as DIRECT | Requires implementation |

DIRECT already has a complete permission graph. There is no duplicate
“all-to-all graph” treatment. On four vertices, an unlabelled connected
undirected tree is either the star or the path; a generic TREE arm would add
no third tree structure here.

All arms retain **one-hop reports of the sender's own direct observation**.
Receiving a report never grants permission to relay it, changes it into direct
evidence, or lets an agent inspect another citizen's memory. CHAIN and STAR
therefore test edge restrictions on the existing direct-report protocol. They
do not implement multi-hop information propagation, a coordinator role, or the
full MARBLE protocols.

DIRECT_UNREAD is an information-access control with a concrete implementation
contract: invoke normal truthful transport, retain its result and costs, and
exclude its reports from policy inputs. It must produce no report READ or
SELECTED events and no report-cued job. Operator inspection of its inbox is not
policy consumption. This does not fabricate a claim that a citizen “ignored”
a message after seeing it. It also does not fabricate shuffled observations.
False or shuffled claims, bounded-memory ablations, relaying, and learned
policies require separately versioned experiments and provenance contracts.

## Fixed sample and counterbalancing

The study has **144 planned fresh worlds: 24 blocks × 6 arms**. World seeds are
`55101` through `55124`; policy-order seeds are a fixed permutation of `65101`
through `65124`. Each
block uses the same world seed, policy seed, initial scene, roster, and
slot-to-seat mapping for its six independently created worlds. These seeds do
not overlap pilot seeds `54101`, `54102`, and `54103`.

Block mappings are all 24 permutations of physical seats `(0,1,2,3)` in
lexicographic order, interpreted as `logical_slot -> physical_seat`. Every
logical slot occupies each physical seat six times. This balances the star
hub and each chain position across the four starting positions. Stable actor
UUIDs are UUIDv5 of the URL namespace and
`hearthbound/communication-preregistration-v1/{world_seed}/{logical_slot}`.
World and episode identities must remain distinct across trials.

The base arm order is `NO_MESSAGES, DIRECT, DIRECT_UNREAD, STAR, CHAIN, CYCLE`.
Zero-based block `i` rotates this order left by `i % 6`. Each arm occurs four
times at each position in the six-arm sequence; within each star hub starting
seat, each arm occurs once at each position. The committed manifest enumerates
all 144 execution slots. Run them serially in that order, with a new JVM,
world, session, and empty agent state for every trial. No shared world's
citizens, rounds, reports, or repeated policy evaluations are independent
replicates. Paired analyses and uncertainty calculations operate on seed blocks.

Policy seeds are assigned before any expanded results to balance first decision
priority as well as network roles. For zero-based block `i`, the first logical
slot is `((i // 6) + offsets[i % 6]) % 4`, where
`offsets = (0, 1, 3, 1, 3, 2)`. Assign the lowest unused seed from 65101–65124
with that remainder modulo four. This offset tuple is the lexicographically
first six-element tuple from 0–3 that balances every physical seat at all four
round phases. The exact seed assignment is stored in each manifest block.
Each logical slot begins six blocks, and each physical seat is first in six
blocks at each round phase. Across all 30 rounds, each physical seat therefore
receives exactly 180 first opportunities over the 24 blocks, in every arm.
Each logical first slot also occurs once at every arm-order offset. This
construction uses only design constraints and no measured outcome data.

The sample size comes from complete seat counterbalancing and a fixed feasible
cohort definition, **not** a power claim or a result-dependent stopping rule.
The nominated scenes do not establish performance across all Minecraft worlds.
Native navigation RNG is still unmatched; matching seeds and declared initial
conditions does not imply byte-identical simulator state.

## Fixture, clock, and budgets

Retain the pilot's scene: two source inventories at `(4,101,8)` and `(4,101,4)`,
two wheat each, and an empty destination at `(10,101,8)`. Physical seats are
`(5.5,101,7.5)`, `(12.5,101,7.5)`, `(14.5,101,10.5)`, and `(12.5,101,12.5)`.
The manifest fixes the sealed arena, cleared sensing envelope, loaded block
rectangle, initial gamerules, time, weather, zero cargo, zero prior jobs, empty
memory, and empty inboxes. Actors start frozen for verification and are released
by the controller at the declared start. The shared destination and roster are
public. Shared source claims only exclude sources an actor already knows
privately; they do not provide a hidden global source menu.

There are 30 controller rounds, at relative ticks 0, 20, …, 580. The order of
phases is motor, idle discovery, communication, idle decision. Each phase uses
the same rotating logical-slot order, starting at
`((policy_seed % 4) + (round % 4)) % 4`. At relative tick 600 the controller
freezes enrolled actors. Independent witnesses may be exported afterward with
their actual capture ticks, provided stable repeated exports verify no change
to scored inventories, cargo, jobs, or journal after the freeze. Do not label
a later RCON capture as having occurred at tick 600. Only verified
deliveries with relative tick `0 <= t < 600` count. Finishing four deliveries
does not stop the world early. A 180-second wall guard limits a stalled run;
it does not substitute wall time for game time or turn an incomplete run into
a valid fixed-horizon observation.

| Resource | Common limit |
| --- | --- |
| Near discovery per idle citizen/round | 75 candidate positions and 4 inventory inspections |
| Outer discovery per idle citizen/round | 75 positions and 4 inspections |
| Selected candidate recheck | 1 fresh direct inspection per idle citizen/round |
| Assignment attempts | 1 per idle citizen/round, following the recheck |
| Send attempts | 1 per citizen/round; at most 120 per world |
| Direct / inbox / decision-view memory | 16 sources / 16 reports / 16 sources |
| Sensor radius | Existing 16-block sensor and loaded-chunk rules |
| Common decision evidence age | At most 200 ticks from the original observation |
| Sender evidence freshness | At most 40 ticks from the original direct observation |
| Report delivery lifetime | At most 200 ticks after delivery; original observation age still applies |

These are common maximum budgets, not equal realized computation. Do not
transfer unused discovery, recheck, assignment, or send capacity between
citizens, rounds, or arms. Preserve existing fresh rechecks, hauling execution,
inventory conservation, and claim rules.

### Recipient choice and cost of restricted edges

For sender slot `s` in zero-based round `r`, propose recipient
`(s + 1 + (r % 3)) % 4`. Choose from the sender's fresh own observations sorted
by source x, then y, then z, taking element `r % observation_count`. With no
eligible payload, record that opportunity without claiming a send attempt.
With a payload, charge one send attempt **before** testing network permission,
the selected edge, distance, deduplication, or recipient acceptance.

NO_MESSAGES records `NETWORK_DISABLED`. A forbidden edge in a topology arm
records `TOPOLOGY_BLOCKED`. Neither retries another peer that round. An allowed
edge proceeds to the existing transport checks, which can still fail. Reports
are synchronous, recipient-private, and never forwarded. The route is the
actual `[sender_uuid, recipient_uuid]`, not a hypothetical path through the
permission graph.

With all 120 payload opportunities available, the fixed rotation permits at
most 120 proposals in DIRECT/DIRECT_UNREAD, 60 in STAR/CHAIN, and 80 in CYCLE.
Real deliveries can be fewer because of missing evidence, distance, duplicate
checks, and other transport conditions. This experiment changes both edge
structure and permitted message volume. Even STAR versus CHAIN changes degree
distribution. It **does not isolate abstract topology from degree, cost, or
spatial opportunity**. Report those mediators and limits alongside outcomes.

## Required communication and physical evidence

Every attempt records its trial/block, world/session, sender, recipient, logical
slots, physical seat assignment, tick/round, source observation identity and
revision, proposed permission edge, edge decision, route, charged budget, and
result/rejection reason. Delivery retains immutable report/message identity,
original observation tick and claimed stock, actual delivery tick, and expiry.
Duplicate transmission must not refresh original evidence or manufacture a
new delivery. Expiry and FIFO inbox eviction preserve durable audit history.

Keep send, rejection, duplicate, delivery, READ, SELECTED, fresh RECHECK,
ASSIGNED, and PHYSICAL_COMPLETED distinct. Link a selected report to a decision,
the exact accepted job, citizen, source, destination, assignment tick, and
independent physical completion. A source recheck must be current and positive
before assignment. Preserve failed rechecks and pending jobs. Classifications
such as never read, never selected, expired, superseded, and evicted can overlap;
their counts must not be added as if they partition messages.

Verify initial and horizon source/destination inventories, every enrolled
citizen's cargo and native job tags, total item conservation, level.dat seed,
world identity, and saved communication history. A genuine completed job later
overwritten in a citizen's current native job tag remains in the durable history
and requires its original physical witness; do not demand that all historical
jobs occupy the final current-job field. Hash all plans, logs, native exports,
results, runtime binding, and independent scorer replay inputs.

The manifest enumerates per-world and per-citizen cost counters: sensor probes
and inspections, rechecks, assignments, sends, each denial category, duplicate
and successful delivery counts, report reads/selections, report-cued jobs and
physical completions, expiry/eviction, and evidence overflow. It also retains
adapter elapsed times. Those times exclude other Minecraft work and are not
total server CPU or matched-hardware measurements. A zero-denominator efficiency
ratio is null. Sending, reading, or repeating information grants no physical
completion or research reward.

The trial/journal capacities remain 4,096 runtime records, 1,024 message records,
8,192 message events, and 2,048 send attempts. Any overflow, missing mandatory
record, or recording error invalidates protocol scoring and remains visible;
silently truncated traces are not valid evidence. A complete report-to-job
chain establishes an observed pathway, not that the same work would have
failed without communication.

## Fixed outcomes and analysis

The **primary endpoint** is independently verified destination wheat gain at
tick 600, with target range 0–4. The **primary contrast** is DIRECT minus
NO_MESSAGES. Prespecified secondary contrasts are DIRECT minus DIRECT_UNREAD,
STAR minus DIRECT, CHAIN minus DIRECT, and CYCLE minus DIRECT, in that order.

Secondary outcomes are first and fourth verified delivery ticks, output-ticks
`sum(wheat_transferred * (600 - delivery_relative_tick))`, physical contributions
per citizen, remaining source stock/cargo/jobs/claims, lifecycle observations,
and computation/communication costs. Output-ticks have range 0–2,400. First or
fourth delivery absent at the horizon is null and censored at 600. A paired
time difference is null if either member is censored or missing; 600 is never
substituted as an observed delivery time. There is no mandatory participation
quota or one-job-per-citizen rule.

The four-item ceiling may cause many ties. Secondary timing outcomes can
describe them, but cannot replace the primary endpoint after results arrive.
Zero output, pending hauls, and null or harmful communication effects are valid
outcomes when the fixed horizon and evidence checks hold.

Report all 144 planned rows with status and null unavailable outcomes. For
each contrast report all 24 block values and missingness, complete-pair deltas,
their mean and median, and positive/zero/negative counts. A contrast needs only
its two named arms to be valid; failure in an unrelated arm does not discard a
valid pair. Show planned, valid, invalid, incomplete, and not-run counts by arm.

For a descriptive complete-pair bootstrap of primary destination gain, sort
complete pairs by block index.
Initialize Python's `random.Random(76124)` separately for each contrast. With
`n >= 2`, draw 10,000 resamples, each of `n` indices
`int(rng.random() * n)` with replacement, and calculate their mean deltas.
Sort those 10,000 means and report entries 249 and 9749 (zero-based) as the
declared percentile interval. With fewer than two pairs the interval is null.
This procedure resamples blocks, not citizens. It describes complete pairs;
it does not correct selective missingness, establish population coverage, or
provide a multiplicity-adjusted topology ranking.

Also report bounds over **all 24 planned blocks**. An observed valid primary
value contributes interval `[y,y]`; an unavailable or invalid value contributes
`[0,4]`. For treatment interval `[a,b]` and reference `[c,d]`, the block
difference is `[a-d,b-c]`. Sum lower and upper endpoints separately and divide
both by 24. Thus a wholly missing pair contributes `[-4,4]`, rather than zero
or removal. For output-ticks use `[0,2400]` instead. These are missingness bounds
for the declared physically bounded target, not confidence intervals. Preserve
raw invalid observations, including conservation violations; do not clip an
invalid value into the valid range to score it.

No p-value threshold, minimum improvement, winning network, or policy-promotion
gate is declared. Additional analyses must be labelled exploratory and follow
the fixed primary report. No significance or benefit is inferred merely from
a valid trace or CI success.

## Failures, stopping, and revisions

Write each slot's plan before dependency setup. Permit one dependency-setup
attempt **before creating any world**, with zero automatic retries, and retain
its complete log. A first setup failure remains unknown performance in its
planned slot. A source, dependency, or configuration fix requires a separately
declared revision and cohort. Each planned slot gets at most one fresh-world
attempt; no replacement worlds or chosen seeds are allowed.

Retain statuses `VALID_OBSERVATION`, `NOT_RUN_SETUP_FAILURE`, `INVALID_PROTOCOL`,
`INCOMPLETE_RUNTIME`, `MISSING_ARTIFACTS`, and `NOT_RUN_COHORT_STOP`. A dependency
failure is not a zero-output world. A partial run has no fixed-horizon primary
outcome. Preserve its observations without silently promoting them to complete
data. Isolated failures do not stop later scheduled slots. No late recovery
after tick 600 is added to the scored window.

The ordinary stop is the end of all 144 slots regardless of results. An early
cohort stop is allowed only for unavailable infrastructure or a protocol breach
requiring a revision. Retain every completed/attempted row and mark the remaining
slots `NOT_RUN_COHORT_STOP`, with a recorded reason. Any change to arms, seeds,
budgets, source/runtime binding, endpoint, or analysis requires a new version
and cohort; do not silently replace trials or pool revisions. Existing pilot
and original reliability evidence remain visible and separate.

## Execution remains blocked

This change supplies no live runner and no new Java arms. The offline validator
requires the exact closed schema, digest, constants, schedule, and complete
denominators. Recomputing a hash after editing a seed, arm, budget, or execution
flag does not make the document valid. Duplicate JSON keys and nonfinite
constants are rejected; the writer refuses to overwrite an existing file.

Before any expanded world, a **separate future binding artifact and validator**
must freeze this design digest, exact runtime commit/tree, protocol/scorer
source hashes, built artifact, resolved dependency identities, workflow, and
launch configuration. Required capabilities include all six arms, audited edge
filtering, truthful delivery without policy exposure, exact seat enrollment,
budget/cost and lifecycle records, no relay leakage, fixed-horizon native
witnesses, fresh-world identity, complete denominators, independent scoring,
and existing Minecraft compatibility checks. Evidence must be hashed acceptance
artifacts at that exact revision, not self-attested booleans. Qualification
worlds and seeds are separate from the 144-world cohort and retained as
engineering evidence. Runtime qualification cannot silently revise this design.

The module's execution check unconditionally refuses even a valid design:

```sh
python3 scripts/test_communication_preregistration.py
python3 scripts/communication_preregistration.py validate docs/experiments/communication-v1.design.json
python3 scripts/communication_preregistration.py check-executable docs/experiments/communication-v1.design.json
```

The first two commands should succeed. The last must exit 2 with
`OFFLINE DESIGN ONLY`. To reproduce the document without overwriting it, run
`python3 scripts/communication_preregistration.py write /tmp/communication-v1.design.json`.
The printed `design_sha256` hashes UTF-8 JSON of the `design` object with sorted
keys, compact separators, and no nonfinite numbers. The enclosing schema and
digest field are excluded from that hash. Validation reproduces the exact
design independently of git working-tree dirtiness, time, environment, or
randomness; the future runtime binding must additionally pin the code revision.

## Research foundation and claim boundaries

[Project Sid, arXiv:2411.00114v1](https://arxiv.org/abs/2411.00114v1),
[MultiAgentBench, ACL 2025](https://aclanthology.org/2025.acl-long.421/), and
[the MARBLE implementation](https://github.com/ulab-uiuc/MARBLE) are primary
references. MARBLE and MultiAgentBench are one research effort, not independent
replications. This design adapts their architecture, evaluation, and protocol
questions; it neither reproduces their experiments nor imports a winning
network claim. Project Sid's action-awareness and information-propagation
questions motivate attributable records and physical checks, without importing
its LLM controller or claiming new social organization.

The verified source mapping in
[the research foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md) supplies the
relevant PA4 readings: P42 for evaluation denominators; P06/P11 for failure,
misalignment, and potentially harmful agreement; P07 for identity/monitoring;
P28/P37 for memory provenance and grounded action; and P30/P34 for explicit
architecture and evaluation boundaries. P04/P15/P19 motivate future strategic
mechanisms, and P32/P33 require explicit policy profiles and payoff coverage
before game-theoretic claims. This six-arm study has neither an empirical
payoff matrix nor learned strategy updates. Those readings remain part of the
research foundation without becoming claims that this study already tests
negotiation, equilibrium, learning, or emergence.
