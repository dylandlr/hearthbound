# Need-driven service architecture v0.20

Status: implementation direction and explicit experimental runtime. The v0.17–v0.19
simulation results remain frozen. This document changes the development route;
it does not turn those results into evidence of useful communication or emergent
occupations. Live acceptance status belongs to the exact tested commit.

## Decision

Move the main development effort into a Minecraft-facing hierarchical controller.
Citizens choose among persistent services using private knowledge. The existing
physical executor remains responsible for navigation, inventory claims, pickup,
delivery, recovery, and authoritative receipts. Learning should increasingly
choose goals, information, partners, and commitments, rather than repeatedly
discovering the elementary movement and item-handling sequence.

The immediate priority is a complete need-to-work-to-withdrawal cycle. The planned
small recipient-only PPO diagnostic is paused. It remains a possible debugging
tool if a specific later failure requires it; it is not the next product milestone.

This is an engineering choice, not a claim that hierarchical control universally
outperforms recurrent PPO. The last pilot learned production but did not establish
a useful communication effect or withdrawal after demand ended. Its reliable
physical executor and provenance infrastructure are more useful foundations than
another unrestricted primitive-action training sweep.

## What is authored and what may emerge

| Authored capability or rule | Choice left to agents or subsequent learning |
| --- | --- |
| Visit a known place and inspect a nearby inventory | Which observation is worth the trip and when to revisit |
| Carry a typed request; exchange it within physical encounter range | Which request, destination, recipient, and timing are useful |
| Reserve a known unit of work and run the hauling motor | Whether to accept it, keep it, release it safely, or choose other work |
| Preserve private, versioned evidence and request expiry | Which memories and partners are useful over repeated demand |
| Verify item transfer and Create processing separately | Estimate service cost and later productive contribution from the corresponding evidence |

No citizen is initialized with a courier profession, a compulsory role quota, or
an occupation reward. A reusable `CARRY_REQUEST` skill is a capability. A courier
occupation would be a repeated, beneficial allocation of that capability that
responds to need. Scripted service selection, a successful request handoff, or a
job label does not establish that result.

## Controller structure

The authoritative server thread reads bounded sensors, advances the current
option, validates decisions, and calls the existing executor. An option is a
temporally extended action with an initiation condition, retained state, and
completion or interruption conditions. A high-level selector acts at meaningful
boundaries instead of replacing an unfinished haul every decision cycle.

The first reusable options are buffer observation, carrying a request, supplying
wheat, and waiting. Their state must identify the evidence and request revision
that justified selection, the actor, the intended endpoint, any reservation, the
physical job UUID, and the last verified progress. A request expiring is not
permission to delete an item, release an uncertain physical claim, or replay a
pickup. Failure and cancellation are explicit outcomes.

Each citizen receives only its own directly witnessed facts and actual delivered
packets. Public map positions and an enrolled population may be configured as
geometry and capability information. Current stock, shortages, other citizens'
private memories, and undisclosed requests must not appear in its menu. In
particular, the old shared colony task board is not a source of candidates for
this controller. A claim arbiter may reject duplicate work for an already known
request; it must not enumerate unknown opportunities for the actor.

## First live vertical slice

An operator registers a wheat buffer and its desired stock, then enrolls citizens
with the same service capabilities. Registration defines a colony need, not an
assigned job. A citizen near the buffer can observe its actual stock. A witnessed
shortfall becomes a versioned, expiring request in that citizen's private memory.
The information reaches another citizen through physical travel and a checked
encounter. A citizen that knows both a live request and a suitable source can
attempt a one-unit commitment and execute it through `SableHauling`.

The controller must retain the full chain from observation through request,
delivery, selected service, native job, and physical completion. Target stock
being met must suppress further new assignments. Withdrawal before pickup uses
the existing safe cancellation boundary. Cargo already picked up must drain
safely or remain explicitly held under the existing recovery rules. Restart must
not create a second job for an unresolved first job.

This initial slice verifies **storage service**, not a processed recipe. One wheat
inserted into a chest is one verified transfer; it is not one unit of Create
production. The production-linked learner must wait for the independent output
witness and job/output attribution rather than accepting a successful service
intent or a transfer event as production.

## Learning boundary

In this first integration the live selector is explicitly
`AUTHORED_LOCAL_CONTEXT_V1`. `ServiceValueLearner` is a separately tested component
and is **not connected to live selection or reward admission yet**. Runtime
status reports zero cost updates, zero production credit, and `learner_ready=false`.
This makes the change a usable execution and coordination architecture with a
learning interface, not a completed learned society.

The first learner is small, local, and CPU-compatible. It accepts only features
from an actor's eligible service menu and settles updates through explicit
outcome records. Observed duration and failure can train execution-cost estimates
without claiming production learning. A production value needs an independently
verified downstream output, attached to the relevant commitment and admitted
once. Request delivery or acknowledgments receive no invented productivity bonus.

The eventual learning unit is a completed or safely terminated option. Its
elapsed time and costs remain visible, so a ten-second action and a ten-minute
action are not treated as equivalent steps. Delayed production evidence may
arrive after a transfer completes; releasing a material claim and settling
productive credit are separate operations. Partner reliability must be learned
from that actor's observed interactions rather than a globally visible score.

Authored priors, exploration, actual parameter updates, and frozen inference must
be distinguishable in status and exports. Shipping a learner class does not mean
the live citizens have learned communication or specialization.

When connecting online learning, keep an instance per citizen unless shared
experience is an explicitly declared communication mechanism. Pooling private
outcomes in a colony-wide learner would otherwise provide an undeclared channel.

## Implementation boundaries

`NeedServiceKernel` holds versioned needs, private indexed knowledge, immutable
packets, unit commitments, and idempotent transfer settlements. The Forge adapter
owns the physical observation and encounter checks; constructing a Java record
alone is not physical evidence. The arbiter's capacity checks apply only to a
request already known to the claimant. Its refusal is an execution result, not a
global opportunity list. Positive revisions must account for work already in
flight and for transfers since the observed stock.

`NeedServiceRuntime` integrates that kernel with the existing local source sensor,
server-lifetime fencing, villager navigation, and native hauling motor. A sticky
ownership marker prevents legacy dispatch or the private communication trial from
also controlling an enrolled citizen. Idle stopped citizens are parked; unresolved
physical work is held. Plain service hauls do not inherit the report-policy
experiment's crash-atomic journal merely by using the same motor.

The first explicit runtime is bounded to eight buffer sites, eight public source
sites, sixteen enrolled citizens, and 4,096 retained events. Request freshness is
600 game ticks and a material commitment's lease is 1,200 ticks; local source
evidence retains the existing 40-tick freshness rule. Exhausted evidence capacity
stops new dispatch and preserves uncertain physical work. A durable archival
strategy is needed before claiming indefinite operation. These limits and the
authored selector are part of this experimental configuration.

The actual command surface, live fixture, and clean-stopped-restart acceptance
are documented in [the v0.20 playtest](NEED_SERVICE_PLAYTEST_V0_20.md).

## Three integrated milestones

| Milestone | Visible capability | Evidence needed to advance |
| --- | --- | --- |
| 1. Need-driven services | Citizens observe a deficit, carry a request, retain a supply commitment, and stop starting work when it closes | Real inventories and job receipts; private knowledge boundary; correct cancellation, conservation, and restart behavior |
| 2. Productive coordination | Several work sites create changing needs; agents choose services using actual costs and downstream production feedback | Output-linked parameter updates; useful recipient behavior; matched frozen/authored and independently trained communication controls |
| 3. Adaptive division of labor | Repeated demand supports persistent specialization, replacement, and reassignment | Benefits over generalist/static-role controls across independent worlds; reduced service activity after demand removal and recovery after its return |

The first two milestones should develop against the same actual Minecraft
interfaces. A fast simulator can accelerate learning when it implements those
contracts; it must not become a separate game whose only deliverable is another
benchmark table. Increase population and task variety after the integrated loop
works. A large initial citizen count is not a substitute for the loop.

These are ordered deliverables, not a promise that emergent occupations will
appear after a fixed amount of training. The runtime, evidence, and learner each
have a concrete failure mode that can be inspected without another broad sweep.

## Economic conditions for courier work

The world must give information a possible use: separated sites, changing private
facts, limited travel time, and productive alternatives to personally inspecting
every location. All actors should retain the same legal capabilities. Do not
force one citizen to stay at a station or require a minimum courier count merely
to obtain the desired pattern.

A powered mill and cheap personal travel may make direct hauling or incidental
report exchange optimal. That is an admissible outcome. Longer routes and several
competing needs are meaningful scenario changes only when disclosed in the
protocol, not added after a failed run to manufacture a courier advantage.

An occupation claim ultimately requires all of the following: repeated service
participation; physically useful effects on recipients and downstream output;
net value after travel and communication costs; persistence over time without a
role label forcing it; adaptation when workers or sites change; and a decline in
unneeded service activity after demand ends. Mere idling from a hard-coded
shutdown rule is a lifecycle capability, not learned withdrawal.

## Faster validation route

Use targeted contracts for ownership, privacy, cancellation, persistence, and
credit deduplication while implementing the architecture. Run one complete live
need-to-service acceptance before undertaking another large learner comparison.
Reserve full held-out, multi-seed cohorts for a meaningful capability change.
Preserve all failed slots in those cohorts, but do not require a new research
campaign to merge every bounded plumbing change.

Maintain separately reported levels of evidence: pure Java contracts, Forge
compilation, live Minecraft lifecycle acceptance, learned policy improvement,
causal communication benefit, and adaptive occupation. Each answers a different
question. Passing one does not silently promote a later level.

## Foundations and reuse

- Existing native execution: `SableHauling`, `HaulClaims`, pickup journals, and
  independently verified completion receipts.
- Existing private-information boundary: the v0.13 private communication pilot,
  rather than the production colony board's shared coordinate menu.
- Existing persistent-goal work: v0.10.3–v0.10.4 already separates sustained
  execution from momentary primitive choice; this pivot consolidates that
  principle around actual service requests and the live executor.
- Sutton, Precup, and Singh (1999), [Between MDPs and semi-MDPs](https://www.sciencedirect.com/science/article/pii/S0004370299000521),
  provides the options framework for actions that extend over time. This document
  proposes an engineering adaptation, not an implementation of every method in
  that paper.
- [Project Sid](https://arxiv.org/html/2411.00114v1) motivates concurrent modules
  coordinated through coherent action ownership. It does not authorize LLM
  controllers or off-thread Minecraft world mutation here.
- [MultiAgentBench](https://aclanthology.org/2025.acl-long.421/) motivates separating
  completion from collaboration and milestone evidence. Its scores are not
  Hearthbound results.

See `PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md` and
`PROJECT_SID_PA4_RESEARCH_FOUNDATION.md` for the existing source and evidence
contracts. The new work preserves the frozen v0.19 policy, environment, training
manifest, and evaluation results.
