# Recurring local demand and physical information services

Status: isolated synthetic research extension to PR #220, based on
`ce38dfa878da71bc2fe17623652fee7690d35d5a`. The first finite-stock pilot and
its negative communication result remain a separate experiment. This version
adds a new environment and a new frozen pilot; it does not activate a new
Forge controller or modify the existing communication qualification study.

## Why this scenario is needed

The first courier pilot allowed production without communication and favored
sharing incidental news during ordinary hauling. Its trained networks
improved over their initial weights but remained weaker than a productive
script; reading messages did not improve output. Those findings do not show
that a courier occupation is impossible. They show that neither useful
communication nor persistent specialization was established in that setting.

This scenario supplies recurring private requests at separate workplaces.
Citizens can save a supplier an inspection trip by carrying a truthful report
about the materials a workshop needs. A citizen who remains at the workshop
can use delivered inputs to keep producing. Every citizen retains all the
same capabilities; no occupation is supplied to the learned actor.

Recurring orders are supplied by the scenario. This is a controlled study of
responding to needs, not evidence that citizens invented requests, contracts,
wages, or a postal institution. The map, report vocabulary, production rules,
and fixed payload scheduler are engineered infrastructure.

## The implemented economy

| Mechanism | Contract |
|---|---|
| Locations | A central depot and two workshops at opposite ends of a supplied one-dimensional map. |
| Material | Two finite input types, A and B; one carried item per citizen. |
| Local demand | Each workshop receives an independently generated order every 28 ticks, requiring 2–4 units of one material type. Future order types are private. |
| Order lifetime | Unreserved units expire after 24 ticks and remain in the unmet-demand ledger. Expiration never deletes material. |
| Production | A citizen physically reserves one available order unit and one matching local input, then works for two ticks. Output is credited only after work completes. |
| Work in progress | Reserved input remains in a separate ledger; unfinished work at the horizon neither disappears nor earns completed-output credit. |
| Individual differences | Independently drawn travel costs and seed-shuffled initial locations, with no profession or citizen-ID feature. |
| Actions | Wait, travel to a location, pick A/B, drop, work, or share. |

Source, carried, workshop, reserved, and consumed inputs reconcile separately
for each material. Issued demand reconciles with completed, expired, pending,
and reserved units. A reservation can finish after its order's deadline;
such completion is counted explicitly as late. A race between multiple
citizens cannot reserve the same remaining unit or physical input twice.

The observation/action boundary excludes remote queues and inventories from
local actors unless they have direct memories or legitimate reports. Known
empty local pickup and unavailable local work are masked from the citizen's
published snapshot; simultaneous races can still cause a denial. Public time
does not disclose the independently sampled future recipe types.

## Information transport

Sharing is an explicit action with a time and personal cost. It transmits one
selected report to eligible citizens at the same location. A working citizen
can receive a report without abandoning its reserved production action, and
can read the report at its next decision. Citizens in transit do not take part
in endpoint conversations.

The fixed scheduler selects a retained remote snapshot. It omits the current
encounter location, where citizens can obtain direct local sight, and uses
sender-owned attempt records to permit delivery to newly encountered peers.
It does not inspect recipients' private knowledge. This is a revised,
explicit transport rule; improved results cannot be attributed solely to
recurring demand when map, actions, and scheduling also changed from v0.1.

Reports retain their original witness, observation time, subject and payload.
Forwarding preserves the parent message and handoff path; it never creates a
new firsthand observation or renews freshness. World/run-scoped identities
distinguish paired trials sharing the same world seed. Sends are frozen from
pre-action snapshots, so a new receipt cannot propagate through an entire
network during one tick.

Five protocols are compared: local physical reporting, blocked transport,
unread payloads, no forwarding of others' reports, and explicit free current
remote information. Unread citizens can carry sealed reports through the
same scheduler while their policy cannot read the contents. Local packet
availability remains observable. Free information is a privileged comparison
and can shift a frozen policy's input distribution.

## Two separate questions

### 1. Can this information channel change a physical outcome?

`scripts/probe_distributed_information.py` runs a balanced mechanism fixture.
It prescribes a resident worker, a carrier, and a supplier, one finite order,
and the same physical travel/share schedule before the supplier chooses its
cargo. Both required material types and both workshop locations are included.
Each of the four fixtures runs with local, unread, and blocked messages,
giving twelve planned slots.

The supplier uses its own observations. Without a readable report, its
declared fallback material is A; balancing A/B prevents choosing only cases
where that fallback fails. With a report, it can choose the requested
material. Pickup, travel, drop, and the resident's work must actually occur
before an output is counted. Pre-choice physical state, actions, and personal
costs are compared across protocols.

This fixture has **scripted roles and zero learning**. It tests the causal
mechanism under prescribed conditions. Its result cannot establish
autonomous specialization, a general communication advantage, or an emerged
occupation. Failed fixture slots remain explicit with unknown output.

### 2. Do freely acting agents learn useful allocation and communication?

`scripts/train_distributed_demand.py` retains the shared independent Double
DQN algorithm from the previous pilot: a small local-observation MLP,
replay, masked online successor selection, target-network evaluation,
duration-correct returns, and separate personal and colony ledgers.
There are no role, message, or delivery bonuses. The network is feedforward
over bounded explicit belief memory; it is not recurrent MAPPO or a
centralized critic.

Training alternates two demand regimes. Recurring demand continues throughout
the horizon. Shutdown demand stops new arrivals at halfway while existing
orders drain or expire. The regime label and future workload do not enter
the actor's observations. Both regimes occur during training, before frozen
evaluation.

The planned pilot uses:

- Four citizens and a 160-tick horizon.
- Three training seeds: 17, 23, and 41; 160 episodes each.
- Twelve held-out world seeds: 9500000–9500011, distinct from training.
- Both demand regimes and eleven policy/protocol slots per seed/world,
  totaling **792 planned evaluation slots**.
- Five protocols for the trained policy; untrained and random local
  baselines; and the same observation-only scripted worker under local,
  blocked, unread, and free-information conditions.

The primary learning comparison is trained versus its initial untrained
network in recurring demand. The primary information comparison is frozen
trained/local versus frozen trained/unread. Scripted communication controls
separately measure whether the generic heuristic can use the channel outside
the prescribed mechanism fixture. A failed pair prevents silent imputation.

The protocol, exact sources, budgets, and seed list are recorded before
training. After each training run, checkpoint hashes are recorded with the
saved models before frozen evaluation. Evaluation loads the saved models and
rejects any weight changes. Intervals resample independent training seeds and paired
whole-world seeds; citizens and time steps are not independent replicates.
Repeated deterministic baselines across training seeds are not new independent
worlds. These are small exploratory experiments, not confirmatory results.

## Interpreting work and courier activity

An empty trip can be scouting or repositioning. A loaded trip can also carry
information. To distinguish them, a trace links a delivered observation to a
completed physical trip only if the citizen already held that exact
observation at departure and delivered it at the destination. Each such trip
is counted once, separately for empty and loaded cargo.

These links establish physical information carriage, not the citizen's
purpose, the recipient's causal reliance, or an occupation. Production,
expired demand, work time, material movement, report delivery, and report
exposure remain separate measurements. Dropping material without a current
unfilled need is an overstock observation, not proof of a bad intention:
later demand might use it.

Early, late, and fully quiet-period counters distinguish the shutdown's
draining orders from behavior after all requests have ended. A reduction in
travel can reflect lower work volume as well as policy adaptation. Establishing
a dedicated information service still requires persistent allocation,
recipient benefit, worker replacement tests, and repeated need changes.

## Frozen v0.2 pilot results

The declared run completed all **792/792 evaluation slots**, with no failed
or missing outcomes, duplicate run IDs, material residuals, or demand
residuals. All three 160-episode training runs changed their neural weights,
for **76,653 optimizer updates** in total. Saved parameter hashes, source
hashes, and the protocol hash were verified after evaluation. The 34 focused
environment, learner, and mechanism tests passed.

The [machine-readable summary](experiments/distributed-demand-v0-2-pilot.summary.json)
retains every condition, per-training-seed means, paired exploratory
intervals, phase counters, checkpoint hashes, and hashes of the full raw
evidence. The raw archive contains all 792 outcome rows, saved initial and
trained models, and complete example traces for the first held-out world
under every evaluated condition and training seed.

### Physical mechanism

All twelve balanced fixture slots were valid. Readable local reports enabled
**4/4 completed outputs**, compared with **2/4 unread** and **2/4 blocked**.
Both materials and workshop locations were included. Before the supplier's
cargo choice, physical state, travel/actions, and personal costs matched.
These prescribed carrier/worker/supplier fixtures demonstrate that reading
a physically carried report can change a real simulated production outcome;
they do not demonstrate learned allocation or an occupation.

### Autonomous production

The table shows mean completed work-order units per 160-tick world. Each
trained condition has 36 evaluations (three training seeds by twelve world
seeds). Script and random baselines repeat the same twelve world outcomes
across training seeds and therefore have twelve independent worlds.

| Policy and information condition | Recurring demand | Shutdown demand |
|---|---:|---:|
| Trained, local reports | 18.22 | 9.39 |
| Trained, blocked messages | 17.17 | 9.56 |
| Trained, unread reports | 17.31 | 9.36 |
| Trained, free current remote information | 6.64 | 3.86 |
| Trained, no forwarding | 17.97 | 9.39 |
| Initial untrained network, local reports | 1.39 | 0.42 |
| Random, local reports | 8.42 | 3.08 |
| Scripted worker, local reports | 20.25 | 11.25 |
| Scripted worker, blocked messages | 26.17 | 13.33 |
| Scripted worker, unread reports | 21.50 | 11.50 |
| Scripted worker, free current remote information | 29.83 | 15.67 |

For recurring demand, trained/local improved over its initial network by
**16.83 units** (exploratory crossed-bootstrap 95% interval **14.83 to
18.95**). It remained below the scripted/local mean and substantially below
the script with blocked transport. The script's priority for sharing can
consume productive time; its blocked-message advantage shows that this
particular reporting rule is not a generally efficient communication policy.

The primary information comparison, trained/local minus trained/unread, was
**+0.92 units**, with an exploratory interval of **-2.45 to +4.06**. Its
per-training-seed differences were **+2.00, +3.33, and -2.58**. This is a
small positive average with inconsistent seed effects; useful learned
communication is **not established**. The shutdown comparison was +0.03
units, also with an interval spanning zero. These few-seed intervals are
descriptive exploratory estimates, not a confirmatory success gate.

Free current information improved the scripted policy but reduced output
for the frozen trained policy. The latter was trained on sparse local
memories and reports; the privileged condition changes its input
distribution. This result is not evidence that accurate information is
intrinsically harmful or an estimate of an optimally trained oracle policy.

### Physical carriage and response to ending demand

Across the 36 trained/local recurring-demand worlds, citizens attempted
2,158 shares, made 856 admitted cross-site report deliveries, and forwarded
35 reports. Provenance linked deliveries to **215 completed empty trips**
and **249 completed loaded trips**. These are distinct counted trips, not
distinct couriers. They establish physical information carriage while
leaving motivation, causal recipient benefit, and occupational specialization
unresolved. There were also 510 drops without a current unfilled local
need; future requests could still use that inventory.

After shutdown orders had fully drained or expired, the trained/local policy
still averaged **13.72 share attempts** and **88.19 travel ticks summed
across four citizens** per world in the quiet observation window. The matched
recurring-demand window averaged 18.42 shares and 96.08 travel ticks.
Differences had exploratory intervals spanning zero, and one training seed
traveled more after shutdown than under continuing demand. Production
correctly reached zero in the quiet shutdown window, but unnecessary
movement and communication did not reliably stop.

The supported result is learned production plus a demonstrated, scripted
information mechanism. A dependable, need-responsive courier occupation is
still unestablished. The next algorithmic question is whether better temporal
coordination and decisions about when to communicate improve recipient
outcomes and reduce activity when demand ends, without an occupation or
message-count reward. That requires a newly declared experiment; this pilot's
settings, checkpoints, and held-out outcomes remain frozen.

## Run

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
python -m unittest discover -s scripts -p 'test*distributed*.py' -v
python scripts/probe_distributed_information.py --output run/distributed-demand-probe/mechanism.json
python scripts/train_distributed_demand.py --episodes 160 --training-seeds 17,23,41 --worlds 12 --agents 4 --horizon 160 --output-dir run/distributed-demand-pilot-v0-2
```

Use a fresh output directory; prior results are retained. The training
checkpoints bind to the exact environment and learner source. This experiment
uses NumPy and local CPU computation, with no LLM calls or API credits.

The [Project Sid/PA4 foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md) and
[research implementation contract](PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md)
continue to govern the difference between communication, participation,
verified outcomes, and society claims. Live promotion needs its own Forge
adapter and physical acceptance. Existing Forge smoke checks validate the
existing mod; they do not make a Python research policy a Minecraft feature.
