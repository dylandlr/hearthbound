# v0.23 — eight-citizen renewable food economy

## Goal and current evidence

This milestone extends Hearthbound from processing a supplied wheat stockpile
to a replenishing crop → flour → dough → bread → meal economy. It is an opt-in
Minecraft controller. Eight citizens have identical capabilities and choose
work from their own observations and locally received facts. There are no
assigned farmer, miller, baker or courier occupations.

The implementation is based on `68829b77ea240eaabc7bb592118124b0258e5c50`, the
newest remote branch head found in the 24 November 2026 branch audit (219 heads,
218 distinct commits). Development branch: `feat/renewable-village-economy-v0-23`,
stacked on `feat/shared-neural-services-v0-22` / PR #225. Earlier draft PRs remain
unmerged. This document will record the exact native trial results after CI;
the initial implementation and constructed tests alone do not establish live
Minecraft functionality.

## Player setup

Use a **new disposable creative world** with Minecraft 1.20.1, Forge 47.4.10,
Create 6.0.8 and the matching Hearthbound build. The setup function clears
`x=0..48, y=100..104, z=0..44`; do not run it over an existing settlement.

```mcfunction
/function hearthbound:village_setup
/tp @s 24 102 20
/hearthbound-village start
```

The setup supplies two districts, eight named citizens, eight planted wheat
plots, irrigation, two regenerative water wells, 64 spare seeds, eight empty
buckets, 32 coal, two Create mills with creative motors, crafting tables,
furnaces and storage. Wheat, flour, dough, bread and filled buckets start at
zero. The glass enclosure protects the development fixture; it is not housing
built by the citizens. Native crop growth runs at `randomTickSpeed=400` for a
bounded demonstration. Normal Minecraft growth uses a different time scale.
The setup explicitly enables `keep-ticking on`: bounded Forge ticking tickets
keep the configured districts active without a connected player. This uses
Forge's native tick scheduler, not direct crop-age writes or generated wheat.
After stopping and resolving work, `/hearthbound-village keep-ticking off`
releases this controller's tickets. These tickets and the opt-in setting persist.
See the [Forge 1.20.1 scheduler patch](https://github.com/MinecraftForge/MinecraftForge/blob/1.20.1/patches/minecraft/net/minecraft/server/level/ServerChunkCache.java.patch)
and [official ForgeChunkManager API](https://github.com/MinecraftForge/MinecraftForge/blob/1.20.1/src/main/java/net/minecraftforge/common/world/ForgeChunkManager.java).

```mcfunction
/hearthbound-village status
/hearthbound-village target 0
/hearthbound-village target 6
/hearthbound-village drain
```

`target 0` withdraws new food-economy work, including meal options; owned work
can finish. `drain` stops new choices while allowing current owned jobs to
finish. When status reports `active=0`, use:

```mcfunction
/hearthbound-village stop
/save-all flush
```

Immediate `stop` cancels nonmaterial observation/wait options but retains and
holds unfinished material ownership. A restart never resumes uncertain work.
There is no command that silently discards held cargo or reconstructs a job.
This is deliberate fail-closed recovery, not a claim of crash-atomic inventory
transactions. A clean drained restart preserves private learned histories,
material stock, native furnace recipe counters and evidence. Stopped native
crops can still grow.

## What each citizen can actually do

| Capability | World operation and completion witness |
|---|---|
| Harvest and replant | Pick up a real spare seed, obtain the mature wheat block's native loot, remove that block, retain all returned loot, consume one seed, place wheat age 0, deliver wheat and seeds to the depot |
| Mill flour | Existing Sable source claim and mill reservation, real wheat pickup and insertion, native Create processing callback, exact flour/byproduct extraction and delivery, then reservation release |
| Prepare dough | Carry flour and a filled water bucket to a real crafting table; query the installed RecipeManager; use its result and remaining-item contract; return the empty bucket and store dough |
| Bake bread | Carry dough into a reserved real furnace; burn actual coal through vanilla ticking; witness cooking progress, input disappearance, bread output and an increment of the furnace's native `RecipesUsed` counter; extract and store bread |
| Refill water | Carry an empty bucket to the configured well and invoke native `BucketPickup`; retain its returned water bucket and store it |
| Eat | Pick up and consume a real bread item; restore the citizen's explicitly authored colony satiety |
| Observe / wait | Move toward a configured site whose facts are missing or stale, or take a bounded idle option |

The skills, installed recipes, station geometry and satiety rules are authored.
The agents do not invent wheat farming, discover recipes, construct buildings,
mine coal or acquire machines in this milestone. Satiety is a mod state, not
vanilla villager hunger, and reaching zero does not kill a citizen. Recipe
processing occurs on the authoritative server thread. A synthetic timer cannot
create bread. Native recipes are checked at execution, including the returned
empty water bucket.

## What learns, and what does not

`VillageWorkPolicy` is a private contextual recursive least-squares learner,
with separate duration and personal-cost estimates for each capability and
an empirical success estimate. Its four inputs are an intercept, bounded route
distance, locally observed deficit and personal hunger. Each citizen updates
from its own settled job's original features, measured duration, sampled
movement distance, sent-packet cost, completion flag and physical receipt.
Outcome UUIDs prevent duplicate learning; a conflicting duplicate is rejected.
Replay of the ordered private outcomes reconstructs the same estimates.

Selection combines these learned execution estimates with explicit authored
recipe utilities. It does not learn the recipe graph, communication protocol,
morality, social identity or a global welfare function. A shared reservation
arbiter can refuse a privately proposed conflicting job; it does not discover
candidate jobs for the citizens. Refusals remain failed outcomes with cost.

The `authored` control has identical sensing, communications, recipes and native
executors but uses the fixed duration/cost priors for selection. Both modes
record private outcomes; control updates are shadow-only. Every decision logs
its complete private offer menu and scores. A separate Python implementation
replays the actual scores and selection from each citizen's own preceding
history and counts choices that differ from the fixed control.

This new action space is **not controlled by the v0.22 neural network**. That
network remains frozen and available in its existing service experiment.
The v0.22 simulator used an 8-block source sensor whereas its native adapter
used 16; stopping a request carrier on source discovery could therefore happen
outside the 12-block peer-contact range. This is a concrete environment mismatch
and a plausible contributor to the previous inactive workers, not a causal
ablation proving a sole cause. Do not retroactively change the frozen v0.22
experiment or report its simulator result as a live advantage. New village
observations and actions are recorded for a later native-grounded neural
training milestone.

## Information and ownership boundaries

Each actor reads configured sites only within 16 blocks. Facts contain an
original observer, position, tick, item counts and crop/water state. Facts expire
after 600 ticks. An authored contact protocol allows at most two peer packets
per 100 ticks, at most eight facts per packet, within 12 blocks and at most two
hops. Local observations and peer claims remain distinguishable; no global
dynamic stock board is passed to the actor.

The evidence contains original observations, packet sends, per-recipient
accepted and rejected facts, evidence IDs used by offers, selected work,
native mutations and settled outcomes. Reconstructing that pathway proves
provenance, not a causal communication benefit. Both selector arms share the
same protocol; this cohort has no no-message or shuffled-message ablation.

Citizens keep sticky ownership markers across stops and reloads. The legacy
colony dispatcher, private communication experiment and need-service controller
cannot claim them. Jobs retain exact citizen, world, session, option and native
motor IDs. Interrupted extraction/insertion/conversion phases stop with cargo
retained. Evidence is bounded (32,768 world records, 4,096 private outcomes per
citizen); exhaustion stops new work. This bounded pilot is not an unattended
long-running production save format.

## Fixed native acceptance

The declared cohort is two world seeds (`23001`, `23002`) × two policies
(`adaptive`, `authored`): all four slots are retained, including missing,
rejected and failed runs. Minecraft entity UUIDs, native loot RNG and server
scheduling are not fully determined by the world seed, so matching seeds is
not deterministic paired physics. No population-level learning advantage is
claimed from this small integration cohort.

Each run uses the same shipped setup function and 7,200 native game ticks.
At tick 3,600 the public target is withdrawn; at 4,200 it returns to six bread
per pantry. Timing tolerance is 20 ticks. No operator crop, inventory, motor,
movement, handoff or completion mutations are permitted after start. The run
then drains existing jobs for at most 2,400 ticks and restarts the server.

Integrity gates require all eight citizens alive, no unresolved cargo/leases,
exact private score replay, local observation/message provenance, unique native
process receipts, and independently read final inventories. The material
equations cover wheat, flour, dough, bread, both bucket forms, seeds and mill
byproducts. Native furnace inventory and recipe counters and Create callback
responses are retained separately from controller totals.

The functional milestone additionally asks for at least four consumed meals,
repeated complete production, at least one replanted plot harvested again after
native growth, four productive citizens, two citizens completing more than one
capability, and productive work after demand returns. These measure a working
colony mechanism. They do not prescribe citizen occupations or prove emergent
society. Completion, participants, role changes, output, communication and costs
are reported separately.

## How the supplied references change the implementation

| Reference | Concrete decision in this milestone | Evidence boundary |
|---|---|---|
| Supplied *Intelligent Agents and Their Applications*, Pham ch. 5, printed pp. 113–117 | Separate sender, recipient, delivery, retained knowledge and bounded message transport | Receipt/acceptance is not production |
| Supplied CSCE 631 PA4 P28/P37 | Keep original observations, accepted intentions, execution, world effects and feedback distinct; learn only from settled original-context outcomes | Memory updates and RLS updates are not deep RL |
| PA4 P42 and [MultiAgentBench, ACL 2025](https://aclanthology.org/2025.acl-long.421/) | Report meals/production, verified participation and coordination cost separately; preserve all four slots | More messages or citizens do not establish collaboration benefit |
| [Project Sid v1](https://arxiv.org/html/2411.00114v1), §§2–3 | One coherent action owner; private observation, decision and physical execution stages; compare expected and observed actions | Architectural adaptation; no released PIANO runtime is imported and no LLM controller is added |
| [MARBLE](https://github.com/ulab-uiuc/MARBLE/tree/eae9f15e5b9f1e808f8ff61800b129d5538c1b47) | Pin scenario, scorer, policy and source revisions; separate the maintained engine from the ACL publication | Not a MARBLE benchmark reproduction |
| Drive `refs`: glossary, Sandholm abstraction, Cemri failure analysis | Explicitly expose the simulator/native sensor mismatch; classify stale stock, contention, custody uncertainty and verifier failures | A simulator win cannot establish native usefulness |
| PA4 P32/P33 | Fixed policies and complete world-level denominators; descriptive paired totals only | No equilibrium, causal advantage, human social validity or population reliability estimate |

The supplied PDFs and exact Drive source identities were already audited in
[the research foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md),
[the implementation contract](PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md), and
[v0.22's source mapping](SHARED_NEURAL_SERVICES_V0_22.md). These sources motivate
mechanisms and measurement; their published results are not Hearthbound results.

## Local and native validation commands

```bash
python3 scripts/test-civilization-contracts.py
python3 -m unittest discover -s scripts -p test_village_economy_evidence.py -v
gradle --no-daemon classes servicePersistenceContracts
```

The `Renewable village economy` workflow compiles the actual pinned Forge/Create
runtime, boots four fresh worlds, runs the fixed native cohort, performs the
clean restart and retains the original artifacts. Constructed contract tests
cover numerical learning, ranking changes, owner isolation, duplicate rejection,
replay, forged production deltas, missing buckets and remote observations.
