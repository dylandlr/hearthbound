# v0.22 — shared neural selection of private Minecraft services

## Status and scope

Built on the latest verified v0.21 head `bc54819cd39c6c624e6ff5b445c2f8359d871211`,
with an isolated branch `feat/shared-neural-services-v0-22`. The v0.21 branch and
its real production/restart evidence remain intact. This increment introduces a
small deep reinforcement learner and frozen Java inference around the existing
Create production executor. LLMs remain deferred.

Local numerical, evidence and standalone Java contracts pass. The fixed
six-slot Forge comparison is required before a live learning milestone is
claimed; its results will be appended after execution. The broader legacy
colony reliability fixture still has the documented post-delivery fall issue.

## What learns

Four identical-capability agents pool experience during offline training. A
shared independent Double-DQN scores each candidate in an actor's private menu.
The network is `30 -> 32 ReLU -> 16 ReLU -> 1`, with 1,537 learned parameters.
Every candidate contributes its existing ten normalized service features:
bias, need units, route distance, evidence age, competition (currently always
zero), private partner success, and four service-kind indicators. The remaining
twenty inputs are the mean and maximum of those features over that same actor's
menu. There is no agent ID, occupation label, remote inventory or peer memory in
the network input.

Available options are supply wheat through a complete mill/output service,
observe a buffer, carry a request toward a public source rendezvous, and wait.
Both neural arms and the authored control use the same menu. They may inspect
any active buffer whose demand is unknown to them. A carry option also ends
when its owner directly observes fresh source stock; this is recorded as
`VERIFIED_SOURCE_OBSERVATION`, never as a peer delivery. The original private
RLS mode retains its earlier eligibility/termination behavior.

Double-DQN uses the online network to select the best legal successor candidate
and the target network to evaluate it. The target is

```
G = sum(k=0..duration-1) gamma^k * reward[k]
y = G + (terminal ? 0 : gamma^duration * Q_target(next, argmax Q_online(next)))
```

Time is measured in seconds, equivalent to 20 Minecraft ticks, with gamma 0.98
per second. Each actor's reward ledger covers its entire sustained option.
Offline reward is 0.75 personal plus 0.25 colony reward. Personal reward is own
delivered synthetic flour minus time, travel and message costs; colony reward
is total delivered synthetic flour; research reward is zero. Observation,
sending, receiving and inserting wheat into a mill confer no production reward.
The shared training reward is not a live observation.

Training uses replay, a target copy every 200 updates, Huber loss, Adam at
0.0005, gradient norm clipping at 5, and epsilon exploration from 0.9 to 0.05.
`protocol.json` pins seeds, budgets, schema, NumPy 2.3.5 and training-source
hashes. The deployable seed **11 was selected before evaluation**, not chosen
from the held-out leaderboard. All three trained and corresponding initial
models are retained with SHA-256 sidecars.

## Frozen Minecraft inference and persistence

The new operator command, usable only while stopped with resolved ownership,
is:

```
/hearthbound-services policy neural
/hearthbound-services policy untrained
/hearthbound-services policy authored
/hearthbound-services policy private
```

Existing geometry/enrollment commands and `/hearthbound-services start`, `stop`,
`status` and `records` still apply. The default remains the verified private RLS
selector. `neural` loads the preselected trained seed-11 resource; `untrained`
loads its exact initialization; `authored` scores the declared service priors
minus 0.3 normalized route distance.

The network never updates live. Every decision logs the eligible features,
all thirty actual inputs, effective scores, selected candidate, policy mode,
model hash and frozen flag. The native private RLS ledger continues as a
**shadow outcome audit** in these three modes and does not select their actions.
Logs distinguish its estimates from the effective neural/authored scores.
Status reports zero neural weight updates.

SavedData persists policy mode and checkpoint hash. A restart rejects a changed
or malformed checkpoint, stays disabled until explicit revalidation, and
retains the existing custody/held-job safeguards. Unknown shapes, nonfinite
weights, mismatched hashes and mixed-owner menus fail closed. Python and Java
have 40 shared numerical forward-pass fixtures, plus aggregate-feature and
corruption tests. The final physical output gate, callback provenance and
byproduct conservation are the existing v0.21 executor contracts.

## Simulator results: all declared slots retained

The bounded surrogate randomizes two-site geometry over 24 held-out world
seeds and four private agents. All arms see the same schedule: initial targets
`[2,1]`, then `[2,4]` at second 40 and `[5,4]` at second 80, ending at second 120.
Three training seeds each receive 500 episodes. Evaluation freezes every model.

| Training seed | Trained mean flour | Same initialization, untrained | Authored mean flour |
|---|---:|---:|---:|
| 11 (preselected deployment) | 7.667 | 6.542 | 6.542 |
| 29 | 7.542 | 0.000 | 6.542 |
| 47 | 7.792 | 0.000 | 6.542 |
| Mean across the fixed three networks | 7.667 | 2.181 | 6.542 |

All **216/216** scheduled slots completed and are present in `results.json`.
There are **24 independent world blocks**, not 72 independent worlds per arm.
The trained-minus-authored mean is +1.125 flour per episode. Averaging the three
fixed trained networks within each world, a 10,000-resample world-block
bootstrap gives a conditional 95% interval of **[0.556, 1.611]**. This interval
does not estimate uncertainty over all possible training runs. The large
aggregate untrained contrast partly reflects two unproductive initializations;
the per-seed table is necessary to interpret it.

These are **synthetic receipts only**. The surrogate does not simulate native
pathfinding, server scheduling, Create's variable yield/byproducts, native
assignment refusal details, or all recovery delays. It uses a fixed 3 blocks/s
movement approximation, one flour per wheat and coarse seconds. The menus,
feature schema, private observation boundaries and option-level reward
structure transfer; numerical performance does not establish Minecraft gains.
The model is feed-forward over private summary features, not a recurrent belief
model. It may alias histories and has no convergence or optimality guarantee.

## Live comparison protocol (frozen before launch)

The new workflow runs all six slots with `fail-fast: false`: worlds 22001 and
22002, each with `neural`, `untrained`, `authored`. Each fresh world has four
citizens, two sources with 16 wheat each, two powered real Create millstones,
and two output chests. Roof installation precedes excavation. Initial citizen
positions, geometry, schedules and time budgets are identical across arms.
Minecraft UUIDs and asynchronous tick details are not controlled by world seed;
this is a small matched integration comparison, not exact trajectory pairing.

Targets change at relative ticks 800 and 1600, with observed intervention timing
recorded and a declared maximum 20-tick tolerance. Output is scored at tick 2400
from verified final-delivery events. All demand is then withdrawn; a maximum
600-tick drain permits existing custody to settle. Drain output is reported
separately and cannot inflate the score. Personal cost at the scoring boundary
includes settled options only; incomplete-option costs are therefore a lower
bound, not a full efficiency estimate.

Each slot checks native source/mill/output inventories and byproducts, original
Create callback records, ownership and event order, no duplicated output
credit, exact Python replay of every Java policy choice, no hidden live neural
updates, and a stopped restart with unchanged policy hash, private ledgers and
inventories. Poor baseline productivity remains a valid result. Missing,
failed or duplicate slots are retained by the summary. The milestone additionally
requires both neural worlds to produce at both sites and settle work selected
from needs observed after each later demand increase.

No no-message/shuffled-message ablation is run here. Packet provenance can show
use, but these three policy arms do not identify communication's causal effect.
Likewise, productive actions by different citizens do not establish learned
occupations, institutions or society-level emergence.

## How the supplied research changes this implementation

| Source | Concrete use in v0.22 | Limit |
|---|---|---|
| Supplied CSCE 631 PA4, P42 (PDF pp. 185–188) | Complete configuration/model hashes; fixed budgets; all failed slots in denominators; world-level uncertainty | Benchmark results do not transfer to Minecraft |
| PA4 P28/P37 (pp. 124–125, 166–167) | Separate private history changes, trained weights, frozen inference and measured outcome | Memory updates alone are not learned performance |
| PA4 P32/P33 (pp. 142–143, 148–149) | Compare explicit policy profiles and state the uncovered strategies | Three arms do not establish equilibrium or strategic robustness |
| Supplied Jain *Intelligent Agents and Multi-Agent Systems*, Pham ch. 5 (printed pp. 113–117) | Separate communicative acts, recipient knowledge and physical effects; typed self-observation termination | A delivered request is not material completion |
| Drive `refs`: glossary, Sandholm abstraction reading, Cemri multiagent failure analysis | Declare which state/physics the surrogate abstracts; retain failure/ownership/provenance evidence | A fast surrogate is not native executor verification |
| [Project Sid v1](https://arxiv.org/abs/2411.00114v1) | Keep perception, sustained service and fast motor responsibilities explicit; server-thread world mutation | Public report/assets are not runnable PIANO; no LLM controller imported |
| [MultiAgentBench](https://aclanthology.org/2025.acl-long.421/) and [MARBLE](https://github.com/ulab-uiuc/MARBLE/tree/eae9f15e5b9f1e808f8ff61800b129d5538c1b47) | Separate final task outcome, intermediate participation and coordination cost; preserve native evidence | Paper and maintained engine are distinct versions of the same research effort |
| [Double Q-learning](https://arxiv.org/abs/1509.06461v3) | Decouple successor action selection and evaluation | Atari findings are not a Hearthbound guarantee |
| [Parameter sharing](https://arxiv.org/abs/2005.13625v8) | Shared policy is a transparent cooperative baseline | No agent indication is used; no optimality/specialization claim |
| [Options / temporal abstraction](https://web.eecs.umich.edu/~baveja/listpapers.html) (Sutton, Precup, Singh 1999) | Discount by the full duration of a sustained option | Private summary features need not be Markov |

The earlier source audit and exact Drive links are in
`PRODUCTION_SERVICE_LEARNING_V0_21.md` and
`PROJECT_SID_PA4_RESEARCH_FOUNDATION.md`.

## Reproduce

Python 3.12 and NumPy 2.3.5; Java 17 for the canonical standalone gate:

```bash
python3 -m pip install numpy==2.3.5
python3 -m unittest discover -s scripts -p test_service_policy.py -v
python3 -m unittest discover -s scripts -p test_shared_service_acceptance.py -v
python3 scripts/test-civilization-contracts.py
OPENBLAS_NUM_THREADS=1 python3 scripts/train_service_policy.py --output /tmp/hearthbound-service-reproduction
```

The reproduction command writes a separate run; compare model/source hashes
before making a reproduction claim. The CI workflow uses the committed frozen
models, compiles actual Forge sources, and runs the declared native cohort.
Training is local/free and requires neither an LLM nor a paid API.
