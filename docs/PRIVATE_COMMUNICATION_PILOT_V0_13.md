# Private-worker communication pilot v0.13

Status: implementation and protocol contract. Live results belong to the exact
tested commit and retained run artifacts; passing offline tests is not a live
Minecraft result. This experiment is stacked on the bounded-discovery work in
draft #215. The draft stack remains unmerged.

## Question and scope

Does bounded one-hop exchange of personally observed source information change
the physical output of four otherwise identical scripted workers, relative to
workers using only their own observations?

The first comparison is **NO_MESSAGES versus DIRECT**. DIRECT allows a sender
to share its own recent direct observation with one eligible recipient per
communication opportunity. It does not forward another citizen's report. This
is a two-condition communication pilot, not yet a comparison of relayed star,
chain, tree, or learned network protocols. Every citizen uses the same worker
policy and can discover, send, receive, and haul. No profession, mandatory
scouting role, minimum participation count, or one-job-per-citizen restriction
is imposed.

The principal endpoint is independently witnessed wheat added to the shared
destination within a fixed **600 game-tick** window. Source depletion, carried
wheat, source claims, incomplete jobs, actual physical receipts, and the complete
communication lifecycle are reported alongside that endpoint. Sending or reading
a report does not award physical completion or research reward.

Prespecified secondary pace measures are the relative tick of the first physical
delivery, the relative tick at which all four items have been delivered (missing
and horizon-censored if incomplete), and cumulative output over time, computed
as the sum of `600 - delivery_relative_tick` for verified completed jobs. They
can distinguish delivery timing when both arms reach the same final output;
they do not replace the primary endpoint after seeing its result.

## Why the production task board is excluded

The normal colony dispatcher can inspect queued task coordinates discovered by
other citizens. Disabling explicit messages while retaining that coordinate
menu would still expose a shared source-location channel. The experiment uses a
separate, explicitly enabled controller with private source candidates. Its
candidate coordinates come only from the worker's bounded direct scan or an
actual report in that worker's private inbox. It never enumerates the colony
task board or another citizen's private memory.

The destination and participant roster are public experiment configuration.
Existing source claims remain shared physical exclusion: a worker may check
whether an **already privately known** source is claimed. Claims do not provide
a catalog of otherwise unknown sources. Citizens can still affect each other
through navigation, contention, and the common inventories in either arm;
NO_MESSAGES means information isolation at the policy boundary, not separate
physical worlds for each worker.

## Matched policy and budgets

Both arms have four stable actor slots and the same explicit policy seed for a
paired scenario. Source choice is scripted and uses neither the fresh world's
UUID nor randomly generated citizen identity as a hidden policy seed. The
common schedule rotates actor priority, preventing an always-first slot from
receiving an undeclared permanent claim advantage.

| Component | Common rule |
| --- | --- |
| Decision cadence | One controller round every 20 game ticks |
| Horizon | 600 game ticks; no actions after the fixed endpoint |
| Private source memory | At most 16 own direct sources, the existing inbox of at most 16 reports, and a rebuilt decision view of at most 16 sources |
| Observation age | At most 200 ticks from the original observation, for both direct and reported information |
| Immediate discovery | At most 75 candidate positions and four inventory inspections per idle round |
| Outer discovery | Existing bounded-discovery cursor: at most 75 positions and four inventory inspections per idle round |
| Candidate recheck | At most one additional direct sensor call per idle round |
| Assignment | At most one assignment attempt per idle round, through the existing hauling motor |
| Outgoing information | At most one send attempt per worker per round; the sender must possess its own direct observation |
| Transport | Existing synchronous, recipient-private, range-12 exchange; direct evidence must be at most 40 ticks old when sent |

The trial's immediate four-inspection cap is explicit and shared by both arms;
the production colony's immediate scan remains unchanged. Direct sensing still
uses the actual 16-block spherical sensor range, current vertical neighborhood,
and loaded-chunk checks. There is no new line-of-sight model. The destination is
excluded from source discovery.

NO_MESSAGES uses the same send selection rule and records attempted transfers
as blocked by the network condition. DIRECT uses the existing checked transport,
which may deliver, reject, or deduplicate a send. Inbox reads cannot sample an
inventory or query the sender's current memory. Newer EMPTY information can
supersede older AVAILABLE information; equal-time direct evidence has priority
over a peer report. A report never becomes a direct observation by being copied
into memory.

These are equal **budget rules**, not equal realized computation. Idle time,
paths, source contention, actual sensor calls, messages, decisions, and accepted
jobs can differ as consequences of the treatment. Report those actual costs.
Adapter elapsed-time measurements, where available, are not total server CPU
measurements or matched hardware performance. They exclude vanilla entity AI,
navigation updates outside the adapter, and other server work. Vanilla entity
navigation and randomness are not removed from the experiment.

## Meaning of report use

The common policy first chooses a privately known source. If that choice came
from a delivered report, the recorded semantics are
`REPORT_CUED_DIRECT_RECHECK`: the report supplied the candidate, then the worker
obtained a fresh positive direct observation before assigning a physical job.
This does not assert that a report alone authorized the haul.

The evidence keeps the following events distinct:

1. A send attempt names its actual sender, recipient, source, world, episode,
   and tick, including blocked, rejected, and duplicate outcomes.
2. A delivery creates an immutable recipient-specific message linked to the
   original direct observation and source revision.
3. A policy evaluation records READ only when it actually consumes that report.
   Operator audit requests never count as consumption.
4. A choice records SELECTED with its decision identity and report identity.
5. A successful fresh recheck and motor assignment bind that decision to the
   exact job, citizen, source, destination, and assignment tick. Rejected or
   empty rechecks retain their decision evidence without assignment credit.
6. Only the motor's verified insertion and completed-assignment checks can add
   PHYSICAL_COMPLETED. The trial also retains each completed job before the
   citizen can receive another assignment.
7. Independent inventory witnesses verify destination gain and conservation.

The new `communicationDispatch.v1` receipt connects this controller to the
existing communication journal without impersonating the older report-policy
experiment. Legacy receipts remain supported. Ambiguous dual receipts and
foreign job bindings do not receive completion attribution.

Journal delivery history is retained even when a report becomes too old, is
superseded, or is never used. Expiry and the common observation-age eligibility
are distinct from delivery. A complete message-to-job chain establishes an
observed information pathway. It does not establish that the same delivery
would have failed without that message.

## Independent worlds and retained denominators

The initial cohort predeclares three paired seeds, **54101, 54102, and 54103**,
with one fresh NO_MESSAGES world and one fresh DIRECT world per pair: six
planned worlds in total. Each world begins with four wheat in two source
inventories and an empty common destination. The fixture records the exact
arena, source stock, actor UUIDs and positions, policy seed, horizon, code
revision, and protocol hashes before the measured window.

Because sensing does not require line of sight, the fixture clears the entire
declared sensing envelope around the enclosed arena before construction and
loads that area. Any policy-facing inventory observation outside the two
declared sources fails the environment contract and remains in the retained
trial evidence. Setup responses, settings, initial actor state, and initial
inventory stock are checked; an operator's intended command is not sufficient.

Paired worlds must match the initial manifest except for the communication arm
and fresh world/session identity. Stable actor slots are reused across a pair
for matching; world and episode identities must still be distinct. The seed and
verified initial manifest do not claim byte-identical vanilla RNG or navigation
state. Independent worlds are the replication units; four citizens in one
world are not four independent trials.

There is one behavioral attempt per planned world. The summary retains failed
setup, invalid instrumentation, missing artifacts, incomplete pairs, zero
output, stalled jobs, and valid null or harmful communication results. A missing
world is not converted to zero output or dropped from the planned denominator.
Revision and protocol changes create a new cohort; older attempts remain
visible and are not pooled silently.

CI tests protocol integrity, independent physical evidence, conservation,
matching, and complete accounting. It does **not** require DIRECT to beat
NO_MESSAGES. Mechanism coverage—an actual isolated direct-only delivery and an
actual complete report-use-to-delivery chain—is reported separately from each
world's performance and validity. With only three paired scenarios, the output
comparison is descriptive and does not establish a general winning network.

The original four-citizen reliability fixture remains unchanged and is a
separate cohort and question. Its historical task-accounting failures are not
erased by passing this private-worker experiment, which deliberately bypasses
the production colony task board.

## Ownership, stop behavior, and compatibility

Only explicitly enrolled disposable-world citizens enter this controller.
Their trial marker excludes the normal colony/follow controller so there is a
single owner of action updates. All Minecraft sensing and mutation remain on
the server thread. Enrollment and startup occur before the measured horizon.

At the fixed endpoint the experiment stops its motor updates and freezes its
actors for stable independent inspection. It preserves incomplete jobs, claims,
and cargo instead of forcing completion. Session loss freezes explicitly marked
trial actors outside the normal dispatcher; this is not an automatic restart
or crash-recovery protocol. Do not enroll valuable production citizens in this
experimental fixture. Ordinary citizens and the existing Create, hauling,
claim, completion, and recovery paths retain their existing behavior.

Validation requires standalone policy contracts, adversarial evidence-validator
tests, actual Forge compilation, the six planned live worlds, and applicable
existing Minecraft acceptance gates. A green offline suite alone is not enough
to promote the runtime or claim a communication effect.

## Reproduction and evidence files

The workflow is `.github/workflows/real-private-communication-pilot.yml`. It
checks out the proposed commit explicitly, writes each trial's plan before
build or server startup, runs all six worlds with matrix fail-fast disabled,
and always attempts artifact upload and the complete-denominator summary.

Offline and compilation checks:

```bash
python3 -m unittest discover -s scripts -p test_private_communication_pilot.py -v
python3 scripts/test-civilization-contracts.py
gradle --no-daemon compileJava compileTestJava
```

One arm can be reproduced with the following command in a fresh checkout with
Java 17 and Gradle 8.8. Use a different fresh checkout for each planned arm;
the runner refuses to reuse its world directory, server configuration, or
terminal result.

```bash
python3 scripts/run_private_communication_trial.py \
  --trial-id pair-01-no-messages \
  --output private-communication/pair-01-no-messages
```

Each artifact includes its predeclared plan, result (including failures),
server and RCON logs, saved world metadata when available, and a SHA-256 ledger.
The summary replays the evidence validators, checks exact code/protocol hashes,
reads native world seed and identity, rejects duplicate or ambiguous trial
artifacts, and reports every scheduled world and pair. The original raw
send/message/event records remain available for inspecting any aggregate count.

Long RCON responses are collected completely before the next observation. The
client sends its read-only delimiter only after receiving the command's first
response, checks request identity and bounds, and does not replay failed
commands. Terminal shutdown uses a single `stop` request without queuing a
delimiter behind it. Existing fixture clients are unchanged.

## Retained first live attempt

The initial revision `dde42d15075248c4b45f1c344ada4910c5dbdc68`, protocol
`bd00b4dd32a31bae78207f1f1b214603679411b164a4c6865d913f573f97de07`, produced
**zero valid performance worlds out of six planned**, with zero completed
pairs. All five worlds that booted stopped during fixture setup, before any
worker was enrolled or measured: the weather check rejected Minecraft's actual
successful response, `Set the weather to clear`. The sixth world failed Forge
dependency resolution before starting Minecraft. These are unavailable
performance measurements, not zero-output observations.

[The original run](https://github.com/dylandlr/hearthbound/actions/runs/45232725636)
and [complete-denominator summary artifact](https://github.com/dylandlr/hearthbound/actions/runs/45232725636/artifacts/14846474629)
remain retained. All seven artifact ZIP digests and 28 internal file digests were
verified, and the original summary was reproduced exactly with the frozen
original code. No member of that cohort reached its measured horizon.

Follow-up fixture corrections accept the captured weather response, send no
extra command after terminal shutdown, and preserve the first failure separately
from cleanup or missing-final-snapshot errors. The first isolated-world cleanup
log showed completed saves followed by the server waiting for its RCON client;
the old client had queued a `list` request behind `stop`. The clean-exit gate and
timeouts remain unchanged. Corrected code and protocol require a separate
cohort; they do not relabel the original attempts as passing.

The same validation round exposed an independent identity problem in the
existing outcome-restart fixture. Its first post-restart receipt and journal
matched the original executor exactly, but its repeated fixed-position query
selected a different nearby Sable and correctly returned `FOREIGN_CITIZEN`.
The second Sable was deliberately present for the original foreign-owner
negative test. This was not a demonstrated idempotence failure for the same
executor; the archived evidence does not distinguish movement from a distance
tie. The fixture correction binds actor-scoped queries to the checkpoint UUID,
waits read-only for that original entity, and preserves the exact evidence,
idempotence, wrong-job, foreign-owner, and revocation checks. No production
journal behavior changes. The [original failed artifact](https://github.com/dylandlr/hearthbound/actions/runs/45232725718/artifacts/14845839719)
remains available separately.

## Research connections

The primary references remain [Project Sid](https://arxiv.org/abs/2411.00114v1),
[MultiAgentBench](https://aclanthology.org/2025.acl-long.421/), and its
[MARBLE implementation](https://github.com/ulab-uiuc/MARBLE), with the source
versions and limits recorded in the
[research foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md).

| Reference | Concrete use in this experiment |
| --- | --- |
| Project Sid | Separate communication, observation, and action ownership; compare intended action with actual physical outcome |
| MultiAgentBench / MARBLE; PA4 P42 | Keep task output, participation, communication, and costs separate; compare coordination conditions explicitly |
| PA4 P06 and P11 | Preserve observable failure modes and harmful or unused information; agreement and message volume are not correctness |
| PA4 P28 and P37 | Bounded, time-scoped memory; explicit observation → choice → accepted action → witnessed outcome |
| PA4 P30 and P34 | Explicit perception, memory, communication, policy, and motor interfaces |
| PA4 P32 and P33 | Independent-world replication and frozen policy coverage; a two-condition result is not an equilibrium analysis |
| PA4 P04, P15, and P19 | Reserve strategic/payoff and resource-regime claims for future explicit economic experiments |

This is an original scripted Hearthbound experiment. It neither reproduces the
papers' headline results nor implements PIANO, natural-language reasoning,
learned collaboration, or societal emergence. LLM controllers remain deferred.
