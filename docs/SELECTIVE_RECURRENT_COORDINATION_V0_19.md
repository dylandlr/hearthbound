# Selective communication and temporal coordination

Status: isolated synthetic extension to PR #221, based on
`6c7a341965a438d518c93e30962f7a6cfd2deea5`. This version preserves the frozen
v0.2 environment and pilot. It adds report-topic decisions, recurrent policy
learning, matched training controls, and recipient-stream counterfactuals.
Minecraft evaluation worlds remain zero; no new Forge controller is enabled.

## Question and comparison boundary

The preceding pilot learned production, but its readable-report advantage
was uncertain and movement/sharing persisted after requests ended. The next
question is whether a policy can choose useful information service and
coordinate over time while reducing activity after demand disappears.

The economy remains the supplied depot/two-workshop map, finite A/B inputs,
recurring private orders, physical travel and cargo, two-tick production,
and independent material/demand ledgers. The inherited rewards remain
verified colony output plus `0.25 * personal reward`. There are no rewards
for sending, delivery, topic diversity, specialization, or an occupation.

Only the new matched comparisons can isolate this experiment's architectural
questions. A numerical difference from v0.2 also includes changed actions,
actor history features, learning algorithm, sampling, and training budget.
It is not a single-factor recurrence comparison.

## Actor, transport, and critic contracts

The adapter in `scripts/selective_communication_env.py` leaves the prior
physics file unchanged. The original eight noncommunication actions retain
their indices. Three explicit actions replace generic sharing:
`SHARE_DEPOT`, `SHARE_WORKSHOP_1`, and `SHARE_WORKSHOP_2`.

A share command sends the chosen retained snapshot to eligible citizens at
the same location. Availability depends on the sender's own evidence,
freshness, co-location, and its own prior attempts. It does not inspect a
recipient's private beliefs or manufacture a recipient-value estimate.
Recipients, reports, vocabulary, and transport rules are engineered; this
is not an experiment in inventing language or postal institutions.

| Interface | Contract |
|---|---|
| Actor input | 52 local features: the previous 37, three available-topic flags, eleven previous-command flags, and elapsed time since the actor's prior decision. |
| Neural state | A private 32-value hidden vector per citizen, reset at the start of each world and updated only at that citizen's decisions. |
| Actor output | A probability distribution over the eleven locally legal actions. |
| Critic input | 87 features: the actor vector and current physical depot, workshop, and worker aggregates. |
| Critic boundary | Used only to learn value estimates during training; no future workload or regime label; never queried during evaluation or execution. |
| Fixed-dispatch control | The same actor input and legal actions, but a legal share command invokes the previous scheduler. Traces distinguish requested and actually sent topics. |

Reports retain their original observer, time, message parent, and handoff
path. Existing conservation, reservation, expiry, simultaneous-send, sealed
transport, and trip-provenance behavior remains in force. A fixed-dispatch
actor remembers its requested command, even when the protocol sends a
different topic. This condition is a frozen-policy protocol intervention.

## Learning implementation

`scripts/recurrent_coordination_policy.py` implements a shared stochastic
PPO actor with a separate centralized training critic. The recurrent actor
is a tanh Elman network. Full individual decision sequences are recomputed
from zero hidden state on each optimization epoch, and gradients propagate
through the complete sequence. The feedforward comparison uses the same
actor width and common initial tensors without a recurrent matrix.

This is a small custom adaptation of MAPPO principles, not a reproduction of
the published implementation or its benchmarks. It uses NumPy on local CPU
and has no LLM calls or paid API dependency.

| Component | Recurrent variant | Feedforward variant |
|---|---:|---:|
| Actor hidden width | 32 | 32 |
| Actor parameters | 3,083 | 2,059 |
| Critic hidden width | 32 | 32 |
| Critic parameters | 2,849 | 2,849 |

The architectures match observations, action space, common initialization,
worlds, and episode budgets. They do not match parameter count: recurrence
adds a 32 by 32 matrix.

Training collects eight complete worlds without updating the behavior
policy, computes generalized advantages, and performs four PPO epochs.
Ratio clipping is 0.2; actor/critic Adam rates are 0.0003/0.001; gradient
norms are clipped at 0.5. The entropy coefficient is declared to anneal
linearly from 0.01 on the first batch to 0.0001 on the final batch. For the
single-batch CI smoke, only the initial coefficient is used. The schedule
reduces continued exploration pressure relative to the small inherited
communication cost; it does not add a quiet-period bonus or change rewards.

Every actor receives the rewards from every world tick, including while
traveling or working. For an action spanning `d` ticks, bootstrapping uses
`gamma ** d`; GAE continuation uses `(gamma * lambda) ** d`, with per-tick
gamma 0.98 and lambda 0.95. Terminal worlds do not bootstrap. Advantages
are normalized over the on-policy batch's individual decisions. The critic
uses half mean squared return error without value normalization or value clipping.

Saved models include actor/critic digests, observation/action contracts,
source hashes, settings, and optimizer counts. They are inference-only
checkpoints: optimizer moments are not serialized, and loading one does not
authorize resuming its training.

## Declared exploratory experiment

The fixed pilot uses 512 episodes for each of three variants under each
training seed, with four citizens and a 160-tick horizon:

1. Recurrent actor trained with readable local reports.
2. Feedforward actor trained with readable local reports.
3. Recurrent actor trained from scratch with unreadable reports.

Training seeds are 17, 23, and 41. All variants share the same world-seed
manifest and alternate recurring/shutdown worlds. There are nine training
runs and 4,608 episode executions over 1,536 distinct training-world seeds.
The three variants intentionally repeat those worlds. Up to three independent
training jobs run in parallel; the final declared checkpoint is always used.

Evaluation uses twelve new world seeds, 9600000 through 9600011, both demand
regimes, and nineteen declared conditions: **1,368 outcome slots**. There
are also **144 planned recipient-stream fork pairs**, covering the primary
recurrent and feedforward policies. Exact slots are recorded in the protocol
before training. No held-out results select checkpoints, budgets, or stopping.

Primary evaluation samples from each policy's learned distribution. Random
uniforms are indexed by training seed, world seed, tick, and citizen; paired
conditions use the same uniforms without call-count drift. Greedy execution
is a separately declared diagnostic. Each script repeats the same twelve
world outcomes across training seeds. Random and learned policies use paired
action streams; repeated citizens and ticks are not independent worlds.

The principal comparisons are recurrent versus equally trained feedforward,
readable versus unread content under the same frozen recurrent policy,
readable-training/readable-execution versus equally trained
unread-training/unread-execution, and activity after shutdown versus the
matched continuing-demand window. Selected/fixed dispatch, neural-state
reset, initial networks, script, blocked transport, and random policies
provide additional diagnostics.

Neural reset removes only the recurrent hidden state. Explicit belief
memory and previous-command features remain. Any test-time intervention
can change the policy's input distribution; separately trained controls
address a different and stronger question about achieved reward after
learning under each information condition.

## Recipient-stream counterfactuals

For every primary policy/world/regime, the evaluator selects the earliest
tick with an admitted report, then the lowest recipient ID (with sender and
source-node tie breaks). It retains a snapshot from **before** that step.
The recipient criterion is fixed and does not select a favorable outcome.

Two continuations start from the same physical state, learned weights,
individual neural states, and random-action tape. Both execute exactly the
same index-step actions and incur identical costs. In one continuation the
chosen recipient can read future reports. In the other, that recipient's
report stream is sealed before the index receipt. Transport, cost, and
other citizens' reading remain available. Previously readable evidence
retains its original freshness; a later sealed packet does not silently
erase that earlier knowledge. Direct observations remain readable.

At the recipient's first subsequent decision, the evaluator verifies that
physical state and prior neural state still match. It records the total
variation between action distributions and whether the same random draw
produces a different action. This measures immediate sensitivity to report
content. It does not by itself establish useful behavior.

Both continuations then run to the original horizon. The evaluator compares
recipient production, material drops, pickups, work/travel, personal costs,
colony production, and other citizens' production. A supplier can help a
different worker produce, so recipient-produced units alone are insufficient.
The readable branch must reproduce the baseline production and demand
ledgers, communication/travel/work counters, per-citizen metrics, and topic counts.
All physical and demand ledgers are checked throughout both continuations.

The estimand is the effect of withholding **one recipient's readable report
stream from first receipt onward under frozen policies**. It is not the
effect of a single message, an optimally retrained communication policy, or
an occupation. Forks preserve prefix evidence IDs and give future evidence
new run scopes. Physical-equivalence comparisons ignore these namespace
differences while preserving all provenance in traces.

Worlds without an admitted report remain `no_opportunity` in the planned
denominator. Their effects are unknown, not zero. Failed or missing pairs
remain explicit; complete-pair production contrasts are not imputed. Fork
effect means are conditional on opportunity coverage. Crossed bootstrap
intervals resample training seeds and whole-world seeds; with only three
training seeds, all intervals remain exploratory. Fork intervals are emitted
only when every planned pair in a policy/regime stratum is valid; partial
opportunity coverage retains conditional means and counts without an interval.

## Frozen v0.3 results

All nine training runs completed their 512-episode budget, totaling 4,608
episode executions, 737,280 world ticks, and 2,304 optimizer updates. Actor
and critic weights changed in every run. The 18 initial/trained checkpoints,
source contracts, protocol hash, and shared training-world manifests were
verified. All **1,368/1,368 evaluations** and **144/144 recipient-fork pairs**
were valid, with no missing, failed, duplicate, or no-opportunity slots in
this run. Both material and demand ledgers reconciled throughout. The
combined suite passed **73 tests**: 39 new contracts and 34 frozen-environment
regressions.

The [frozen numerical summary](experiments/selective-coordination-v0-3-pilot.summary.json)
contains all conditions, seed means, exploratory intervals, validation, and
hashes for the complete raw evidence. The archive retains all outcome rows,
all models and training-batch records, 114 baseline example traces, and 24
fork-branch example traces. Examples use the first held-out world under all
conditions and training seeds; they are not selected for successful behavior.

Mean completed work-order units per 160-tick world:

| Condition | Recurring | Shutdown |
|---|---:|---:|
| Recurrent, readable local reports | 20.36 | 8.53 |
| Same recurrent model, unread at evaluation | 20.39 | 8.53 |
| Same recurrent model, blocked transport | 20.39 | 8.53 |
| Same recurrent model, fixed report scheduler | 19.97 | 8.19 |
| Same recurrent model, neural state reset | 17.03 | 7.03 |
| Same recurrent model, greedy execution | 3.28 | 1.61 |
| Initial recurrent network | 7.78 | 3.11 |
| Equally trained feedforward, readable reports | 19.83 | 8.14 |
| Same feedforward model, unread at evaluation | 19.28 | 8.19 |
| Same feedforward model, blocked transport | 20.31 | 8.83 |
| Same feedforward model, fixed report scheduler | 19.61 | 8.44 |
| Same feedforward model, greedy execution | 3.28 | 1.61 |
| Initial feedforward network | 7.58 | 2.97 |
| Recurrent trained and evaluated unread | 19.94 | 8.31 |
| Unread-trained recurrent model, readable at evaluation | 20.08 | 8.31 |
| Script, readable reports | 22.25 | 11.33 |
| Script, unread reports | 21.58 | 10.75 |
| Script, blocked transport | 25.92 | 13.42 |
| Random, readable reports | 7.53 | 2.94 |

Learning improved recurrent recurring-demand production over initialization
by **12.58 units** (exploratory 95% interval **10.86 to 14.33**). Resetting
this frozen model's neural state reduced output by **3.33 units** (interval
**2.00 to 4.69**). Its trained behavior depends on that state, while the
reset remains an intervention on the execution distribution. The recurrent
advantage over the equally trained feedforward policy was only **0.53**
(interval **-1.58 to 2.42**); recurrence superiority is not established.

The recurrent readable-minus-unread-at-test difference was **-0.03 units**
(interval **-0.17 to 0.00**). Comparing the separately trained readable and
unread recurrent models gave **+0.42** (interval **-0.86 to 1.67**). The
selected-topic versus fixed-scheduler comparison was **+0.39** (interval
**-1.03 to 1.75**). None establishes a useful learned communication advantage.

### Recipient response versus productive benefit

Every planned world supplied a first-report opportunity. The table reports
the readable-minus-sealed report-stream effect; each row has 36 paired
seed/world continuations.

| Policy / demand | Mean first-decision TV distance | Changed first sampled actions | Mean colony output effect | Positive / zero / negative output effects |
|---|---:|---:|---:|---|
| Recurrent / recurring | 0.00159 | 0/36 | 0.000 | 0 / 36 / 0 |
| Recurrent / shutdown | 0.00159 | 0/36 | 0.000 | 0 / 36 / 0 |
| Feedforward / recurring | 0.00679 | 0/36 | +0.056 | 5 / 28 / 3 |
| Feedforward / shutdown | 0.00679 | 0/36 | +0.028 | 2 / 32 / 2 |

Report content slightly changes the action distributions, but the common
first-decision draws did not choose different actions. Later decisions can
still diverge: the feedforward recurring suffix effect spans **-0.25 to
0.42** under the exploratory bootstrap and its shutdown effect spans **-0.17
to 0.22**. Neither supplies a robust production benefit.

All 72 recurrent pairs showed zero observed colony and recipient production
effect. This is a finite-sample result for the selected recipients and
action tapes, not proof that every possible report has exactly zero effect.
The two regimes share their pre-shutdown histories and must not be treated
as 72 independent physical worlds. Reading and transport were separately
checked; the zero production result does not come from silently skipping the
intervention or removing its denominator.

The recurrent recurring worlds still contained 968 admitted reports, 57
forwarded reports, and deliveries linked to 450 empty trips and 257 loaded
trips. Those observations establish physical information carriage. Their
coexistence with negligible recipient benefit demonstrates why carriage
counts alone do not establish a courier occupation.

### Withdrawal after demand ends and execution risk

In the fully quiet shutdown window, the recurrent policy averaged **17.31
share attempts** and **153.22 travel ticks summed over four citizens**.
The matched continuing-demand window averaged 17.75 attempts and 139.89
travel ticks. The travel difference was **+13.33 ticks**, with exploratory
interval **6.25 to 20.47**; it increased in all three training seeds.
The sharing difference of -0.44 had an interval spanning zero. Production
correctly reached zero once orders were absent, but the agents did not
reliably withdraw unneeded activity. The feedforward policy also increased
quiet-window travel (+11.92 ticks).

Greedy execution is a material failure mode: both learned architectures
averaged only 3.28 recurring-demand units. Seeds 17 and 23 produced zero in
every greedy world. In the retained first-world recurrent traces, those
policies predominantly waited after a few initial actions. The declared
stochastic policy must not be silently exported as an argmax controller.

This experiment supports learned production and dependence on recurrent
state, but not a communication-driven occupation or reliable service
withdrawal. The next diagnosis should address how learning attributes later
recipient/colony gains to a specific communication decision, alongside the
tradeoff between useful work, exploration, and idling. These are hypotheses
for a new declared study, not demonstrated explanations of this result.
The current settings, checkpoints, and held-out evidence remain frozen.

## Validation and reproduction

The tests cover local/private boundaries, topic selection, old-physics
equivalence, sealed forwarding, retained evidence, numerical actor/critic
gradients, full recurrent BPTT, PPO clipping, duration-correct GAE,
continuous reward accounting, frozen execution, and paired counterfactuals.
The CI smoke uses a separate small development seed/budget and retains its
own outcomes, checkpoints, and traces.

```powershell
$env:OPENBLAS_NUM_THREADS = '1'
python -m pip install numpy==2.3.5
python -m unittest discover -s scripts -p 'test*selective*.py' -v
python -m unittest discover -s scripts -p 'test_recurrent_coordination_policy.py' -v
python scripts/run_selective_coordination.py --episodes 512 --training-seeds 17,23,41 --worlds 12 --evaluation-seed-start 9600000 --agents 4 --horizon 160 --workers 3 --output-dir run/selective-coordination-pilot-v0-3
```

Use a fresh output directory. The runner refuses to overwrite prior evidence.
The initial small development smoke is not mixed into the declared pilot.

## Research basis and limits

- [Yu et al., *The Surprising Effectiveness of PPO in Cooperative Multi-Agent Games*, NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/file/9c1535a02f0ce079433344e14d910597-Paper-Datasets_and_Benchmarks.pdf): local actors, centralized training values, and conservative on-policy reuse inform this adaptation. Its benchmark results are not Hearthbound results.
- [Singh et al., *Learning When to Communicate at Scale*, ICLR 2019](https://arxiv.org/abs/1812.09755): learned communication gating motivates making service optional. Hearthbound retains physical discrete report actions and does not implement IC3Net's continuous channel.
- [Lowe et al., *On the Pitfalls of Measuring Emergent Communication*, AAMAS 2019](https://www.ifaamas.org/Proceedings/aamas2019/pdfs/p693.pdf): separate signaling from recipient response, intervene on information, and compare freshly trained communication controls to address test-time distribution shift. Our total-variation diagnostic is not the paper's mutual-information CIC metric.
- The [Project Sid/PA4 foundation](PROJECT_SID_PA4_RESEARCH_FOUNDATION.md) and [research implementation contract](PA4_MARBLE_IMPLEMENTATION_CONTRACT_V0_2.md) continue to govern local knowledge, outcome verification, independent-world evidence, and runtime promotion.

Even improved production and recipient sensitivity would leave persistent
specialization, reliable service withdrawal/reappearance, worker replacement,
large-population behavior, and real Minecraft transfer to be established.
