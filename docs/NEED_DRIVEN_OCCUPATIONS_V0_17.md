# Need-driven occupations: physical information and learned work allocation

Status: **isolated simulator research**, based on PR #219 at
`7d2f8710b832040ee72f74646738490481139b0d`. This extension does not enable a new
Minecraft controller. It does not change the existing direct-observation
communication conditions or the frozen 144-world study.

## The design decision

A courier should become useful because information has to reach someone who
can act on it. Citizens have ordinary capabilities: observe locally, remember,
travel, exchange a report, and perform physical work. A policy learns when to
use those capabilities. An occupation is an observed, persistent pattern of
useful work; its name is not a required policy output or a reward target.

For example, a remote workshop learns that it lacks timber. Nearby workers
know this; a forest crew does not. One citizen can take the request to that
crew while the workshop workers continue producing. If repeated deliveries
save more productive time than they cost, specializing in that service may
be beneficial. When demand disappears or a communication technology replaces
the journey, the policy should have an opportunity to change its work.

This is a **design hypothesis**, not an observed Hearthbound result. Generic
capabilities and an environment with local information are engineered. Their
allocation, persistence, and eventual social organization are the proposed
learning outcomes. A typed stock report is sufficient for this experiment;
inventing a language is a separate research question.

## First bounded pilot: learning occurred, useful couriers did not emerge

The fixed pilot used four citizens, 120 training episodes for each of seeds
17, 23, and 41, then twelve held-out world seeds across eight evaluation
conditions. All **288 planned evaluation slots** completed with zero material
conservation violations. These are paired runs across twelve world seeds and
three training seeds, not 288 independent layouts. Scripted/random outcomes
repeated across training seeds are also not independent new replications.
The 27 mechanism/learner tests passed. The frozen networks underwent 34,419
optimizer updates during training and none during evaluation.

| Frozen policy and information condition | Mean production batches |
|---|---:|
| Scripted local work baseline | 4.500 |
| Trained, no messages | 1.333 |
| Trained, unread payloads | 1.333 |
| Trained, physical local reports | 1.222 |
| Trained, original reports only | 1.222 |
| Trained, free current remote information | 0.528 |
| Random local actions | 0.500 |
| Initial untrained local network | 0.000 |

Trained/local exceeded the same initial networks by 1.222 batches, with an
exploratory crossed-bootstrap interval of [0.333, 2.333]. It underperformed
the scripted policy by 3.278 batches. Reading reports changed production
by -0.111 relative to unread reports, interval [-0.583, 0.333]. These small
pilot intervals are descriptive, not confirmatory evidence of general
superiority. Free information changes the network's input distribution;
its low score does not establish that information is intrinsically harmful.

Across the 36 trained/local runs, citizens attempted 2,585 shares, admitted
103 cross-site report deliveries, and forwarded another witness's report
only twice. They also incurred 1,563 denied pickups. Exposing reports in
538 decision inputs does not establish useful information use. Turning off
relaying produced the same output in every matched run. There is **no
demonstrated communication benefit or dedicated courier occupation**.

The result identifies two remaining problems: the learner still performs
basic work poorly, and this small economy does not require a specialized
information service to perform well. Increasing a courier counter or
awarding a sending bonus would not resolve either problem. Preserve this
pilot and use a separately declared scenario for recurrent local demand
and later algorithm comparisons. Full numerical summaries, per-seed
results, source hashes, and validation counts are in
[courier-v0-1-pilot.summary.json](experiments/courier-v0-1-pilot.summary.json).

## Implemented research slice

The new files are `scripts/courier_economy_env.py` and
`scripts/train_courier_economy.py`, with focused tests beside them. The
environment has a hub and four known resource sites. Agents carry individual
items, travel over elapsed simulation ticks, and deliver to the hub. A
synthetic production event consumes one unit of each input. Finite source,
cargo, hub, and consumed inventories are reconciled independently of policy
claims.

The action menu contains waiting, travel to a location, pickup, drop, and
sharing a report. There is no courier assignment, profession identifier, or
bonus for sending messages. Agents use the same capabilities and shared
policy parameters. Individual travel costs can differ without fixing jobs.
Report payload selection is an explicit fixed scheduler in this first
slice; choosing a payload or recipient is not yet a learned behavior.
Each carrier sends a given observation at most once, even if it later meets
new recipients. This extra dissemination restriction is part of the pilot,
distinct from recipient duplicate suppression.

Each citizen observes its own state, publicly supplied static geography,
nearby citizens, and bounded private memories. Source quantities and hub
inventory are not a global blackboard in the local protocol. Direct sight
requires physical presence; a report remains a report after receiving or
forwarding it. The actor does not receive the evaluator's full event log or
other citizens' private memories.

This small economy can test whether local information improves resource
allocation and whether a learned policy chooses to share it. Its single hub,
finite stocks, supplied map, and fixed report scheduler do **not** establish
an economy of multiple settlements, self-created service contracts, or a
dedicated courier occupation. Incidental sharing while hauling may be the
best strategy. A result with no dedicated couriers is valid.

## Learning algorithm and honest scope

The implemented baseline is **parameter-shared independent Double DQN** with
a small NumPy MLP, replay, a target network, legal-action masking, and
discounting over the actual duration of travel options. Agents learn from
verified synthetic production and personal costs. Their policy inputs are
local; the common training reward is not a globally readable actor input.
Personal and colony reward totals remain separate in the evidence.

This is real neural weight training, with save/load checks and frozen
evaluation. It is not MAPPO, a centralized-critic implementation, a recurrent
network, learned language, or a proof of specialization. Bounded explicit
belief memory and learned recurrent memory are different mechanisms.
Shared independent learning is an economical baseline, but delayed team
credit and changing fellow agents can make coordination difficult.

The next algorithm comparison should add a recurrent shared actor and a
training-only centralized critic, with matched training budgets and local
execution. MAPPO is a justified cooperative baseline, not a guarantee of
occupations [1]. Role-conditioned approaches such as ROMA and RODE can be
separate comparisons if a simpler policy does not specialize [2, 3]. Their
regularizers or restricted action spaces introduce biases that must be
reported; a role-diversity bonus must not become the success metric.

## Physical report contract

A future Forge relay adapter needs a separate versioned protocol. The
existing private-communication pilot deliberately permits only a sender's
own direct observations. Forwarding received reports changes that contract.

Every report must retain its original observation identity, original
observer, world/session scope, subject, payload, and observation time. Each
handoff adds the immediate sender, recipient, delivery tick, physical
locations, and parent message reference. A carrier is not automatically the
original witness. Copying or forwarding does not renew freshness or convert
a peer claim into direct evidence.

For both the research environment and any future adapter:

- Communication has finite capacity and an action/time cost. Local delivery
  requires a physical encounter; a travel intention is not arrival.
- Choices are validated against pre-action observations. A report received
  during a tick cannot be recursively forwarded through that entire tick.
- Duplicate, blocked, empty, expired, and unread attempts remain observable.
  Retransmission must not manufacture rewards or a new observation time.
- Delivery, exposure to policy inputs, choice, and independently checked
  work outcome are separate evidence stages. A report in an observation is
  not proof that the network relied on it.
- A received stock claim can guide travel. Actual pickup still checks the
  current source; completion requires the physical inventory transition.

## Controls in the baseline runner

| Condition | Intervention | Interpretation |
|---|---|---|
| `local` | Information travels through co-located sharing and private memory | Proposed physical information condition |
| `no_messages` | Sharing attempts still consume their cost but carry no reports | Frozen-policy dependence on the channel |
| `unread` | Sealed reports may arrive and be forwarded; their contents are excluded from policy input | Payload-reading ablation; local packet availability remains observable |
| `no_relay` | Only original firsthand reports may be sent | Isolates permission to forward another witness's report |
| `instant` | Current remote information is made freely available | Explicit privileged-information comparator; not a realistic local protocol or a guaranteed performance ceiling |

The same held-out world seeds are evaluated with trained, initial untrained,
random, and observation-only scripted policies. For protocol interventions,
the trained checkpoint is frozen. Changed observations can change its
trajectory and therefore its realized costs. The comparison estimates the
total effect of the protocol for that policy; it does not hold every future
movement or message count fixed.

Training seeds and evaluation world seeds are distinct. The protocol is
written before training, along with source hashes and budgets. Counts,
failures, zero outputs, and all scheduled evaluation slots remain in the
report. Uncertainty is calculated over whole worlds and training seeds,
never treating citizens within a world as independent replications. Small
pilot intervals are descriptive and do not qualify the Minecraft runtime.

## What would count as an emergent courier occupation?

The first three requirements establish useful specialization. The last two
are needed before claiming a durable occupation or institution.

1. **Voluntary allocation:** identical generic capabilities; no assigned
   courier, fixed role ID, scripted delivery schedule, or delivery-count
   reward. Agent identity permutations must not determine who does the work.
2. **Persistent behavioral specialization:** sustained carriage and handoffs
   of others' information across multiple work cycles. A few incidental
   reports during a hauling trip are recorded as incidental communication.
3. **Useful and need-dependent work:** recipients change decisions and
   improve independently verified outcomes. Suppression or payload changes,
   no-relay controls, and replacement of frequent carriers distinguish
   causal usefulness from activity. Free communication or reduced demand
   should alter the allocation when delivery stops being worthwhile.
4. **Viable individual incentives:** the service supports the worker's own
   needs through funded payment, reciprocal aid, or an explicit colony
   sharing rule. Shared training reward alone does not demonstrate a labor
   market. Payments must conserve resources and never reward circular
   self-generated requests.
5. **Social persistence:** other citizens repeatedly request or rely on the
   service; the arrangement survives changed workloads, individual loss,
   and replacement. Reputation and contracts need evidence of their own.

The evaluator can infer a descriptive label after observing these
behaviors. It must not feed that label back as a required profession. The
number of professions, couriers, guilds, or political groups is not a preset
success target. Message counts and apparent correlation can be misleading
without interventions on recipients' information [4].

## The next environment increment

After the basic mechanics and learning baseline are measured, introduce
multiple persistent work sites with independently changing local demand.
Production and travel must compete for a citizen's time, and repeated
requests must create a reason to batch deliveries. Compare the same world
under local information, costly physical relay, free remote information,
and reduced demand. Add identical-capability fixed-role and flexible-role
baselines. Freeze layouts, workload schedules, action budgets, and policies
before evaluating them.

### Reproduce the bounded pilot

From the repository root, with NumPy installed:

```bash
OPENBLAS_NUM_THREADS=1 python -m unittest discover -s scripts -p 'test*courier*.py' -v
OPENBLAS_NUM_THREADS=1 python scripts/train_courier_economy.py --episodes 120 --training-seeds 17,23,41 --worlds 12 --agents 4 --horizon 96 --output-dir run/courier-pilot-v0-1
```

On PowerShell, set `$env:OPENBLAS_NUM_THREADS = '1'` before running the same
Python commands without the leading environment assignment. The runner refuses
to overwrite a nonempty output directory. Each independent training/evaluation
trajectory has its own run identity even when it shares a paired world seed.
Checkpoints bind to the exact environment and learner source hashes.

Agent traits can change endurance, local familiarity, risk preference, and
learning history, but should not encode professions. Practice can make a
service cheaper and repeated successful interactions can make a partner
more trusted. These mechanisms create possible feedback loops; they do not
guarantee an efficient or fair society.

Longer evaluation should record service participation, worker switching,
task delays, unmet requests, resource output, personal welfare, delivery
cost, and response to worker loss separately. A courier that continues
delivering obsolete reports is a policy failure, even if its occupation
label is stable.

## Forge integration boundary

Promote the new protocol only after a local-observation adapter, bounded
server-thread execution, durable private reports, chunk/restart behavior,
and physical pickup/drop witnesses are implemented and tested. Reuse
Hearthbound's action ownership, state-version checks, and independently
verified inventory evidence. Add actual Forge compilation and fresh-world
acceptance at that stage. The current extension is synthetic and starts
**zero Minecraft worlds**.

Project Sid motivates coherent action and communication, persistent
specialization, and social measurements. Its language-model-based role
labels and inherited knowledge are not evidence of de novo occupations in
this non-LLM pilot [5]. MultiAgentBench's separate completion, contribution,
and coordination measurements remain useful; MARBLE is its versioned
implementation, not an independent replication [6]. See the existing
[Project Sid/PA4 foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md) and
[implementation contract](PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md) for
the PA4 mappings, source limits, and existing gates.

## Primary sources

1. Yu et al., *The Surprising Effectiveness of PPO in Cooperative Multi-Agent
   Games*, NeurIPS 2022: https://proceedings.neurips.cc/paper/2022/hash/9c1535a02f0ce079433344e14d910597-Abstract-Datasets_and_Benchmarks.html
2. Wang et al., *ROMA: Multi-Agent Reinforcement Learning with Emergent Roles*,
   ICML 2020: https://proceedings.mlr.press/v119/wang20f.html
3. Wang et al., *RODE: Learning Roles to Decompose Multi-Agent Tasks*, ICLR
   2021: https://arxiv.org/abs/2010.01523
4. Lowe et al., *On the Pitfalls of Measuring Emergent Communication*, AAMAS
   2019: https://arxiv.org/abs/1903.05168
5. Altera.AL, *Project Sid: Many-agent simulations toward AI civilization*,
   version 1: https://arxiv.org/html/2411.00114v1
6. Zhu et al., *MultiAgentBench*, ACL 2025:
   https://aclanthology.org/2025.acl-long.421/ ; official implementation:
   https://github.com/ulab-uiuc/MARBLE
