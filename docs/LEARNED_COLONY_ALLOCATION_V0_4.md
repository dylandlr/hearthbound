# Learned colony task allocation v0.4 — pilot protocol

Status: implemented abstract-simulator experiment. No Minecraft policy control,
neural navigation, emergent occupation, or learned communication is supplied.
This stacks on PR #196's verified scripted execution boundary; its Python tensor
is a new simulator contract, not the existing Forge observation tensor.

## Question and primary comparison

Can reward training improve a shared task-selection policy over its untrained
initialization when two workers must obtain complementary finite resources?
Compare the same trained policy against a balance-aware scripted heuristic,
nearest-source heuristic, and random policy. Outperforming untrained weights is
different from outperforming a strong script or showing reinforcement learning
is necessary. Report those comparisons separately even if they are negative.

Use two workers initially to isolate allocation and contention. A four-worker
run is a separately labeled scaling experiment, not silently pooled evidence.
The deterministic shared actor has no citizen identity input and starts both
workers at the hub. Its initial choices are symmetrical. Timing, contention, and
public in-transit work may subsequently break symmetry; this is not a learned
roles experiment.

## World and information contract

Four sites supply two resource types, with two sites of each type. Their slot
ordering, coordinates, initial quantities, and extraction priority are generated
from separate deterministic streams. Each site has one to four items. Resources
never replenish. A hub consumes one item of each type per production batch.
The episode lasts 64 ticks even after the first successful batch.

All actors receive the same supplied map, site types, public hub ledger, public
cargo-in-transit counts, and inspection intentions. Exact remote source stock
is hidden. Inspecting a site spends travel ticks and establishes a local direct
observation. Hauling requires being at that site with a positive direct view;
extraction occurs at task start and delivery after travel to the hub. Source
knowledge refreshes only when idle and physically present. Repeated remote reads
and action masks cannot inspect hidden stock.

All idle actors decide from snapshots before any of their actions mutate stock.
A precomputed policy-independent tick priority arbitrates simultaneous pickups.
Inspection intentions do not reserve stock. Cargo still in transit at the fixed
horizon is conserved and receives no delivery/production credit.

The nine options are WAIT, four INSPECT_SITE options, and four HAUL_SITE options.
The 38 features are six global features (time remaining, two hub buffers, two
in-transit counts, at-hub flag), then eight features per site: two type flags,
travel distance, known flag, observed quantity, observation age, at-site flag,
and other workers' announced inspection count.

Normalization: hub quantities /8 (finite maximum per type); site quantities /4;
distance /24; age and remaining time /episode horizon; public in-transit counts
/worker count; other inspections /max(1,worker count-1). The scripted balance
policy converts hub/transit features back into matching item units. Feature
order, normalization, and environment/trainer source hashes are bound into the
checkpoint contract. This public ledger is deliberately supplied scaffolding;
there is no communication-benefit claim.

The standard map uses nonzero integer positions between -6 and +6. A long-route
holdout uses sites from -12..-7 and +7..+12. A scarcity holdout limits type-B
sites to one item each. The material upper bound is the lesser initial total
of the two types; it does not account for travel or imply that this bound is
attainable within the time limit.

## Learning and time accounting

Use a 38→64→9 ReLU shared network, independent per-worker Q transitions,
Double-DQN targets, uniform experience replay, and a lagged target network.
No expert action labels, hidden potential outcomes, resource coordinates as
answer keys, or held-out trajectories are supplied as training targets.

Colony reward is exactly the number of batches physically completed in this
abstract simulator, counted once in colony metrics. Each worker receives the
common colony reward for learning. Personal reward is -0.002 per tick, with an
additional -0.05 per denied pickup. This fixed-horizon living cost is constant
across policies except for denials; it is not a differential movement penalty.
Record actual travel ticks separately. Scalar training reward is colony reward
plus 0.25 times that worker's personal reward. Keep both components in traces.

Each option transition accumulates every intervening tick's discounted reward.
Discount gamma is 0.98 per simulation tick; bootstrap uses gamma^duration.
Waiting, failed pickups, and busy travel all consume actual ticks. Remaining
time is observed, and the fixed finite-horizon terminal does not bootstrap.
Tests require every worker's episode ledger to cover every tick once.

Training settings are fixed before this pilot: Adam rate0.001, Huber loss delta1,
global gradient norm cap5, batch32, replay starts at64 transitions, capacity20000
with oldest2000 discarded on overflow, target copy every200 optimizer updates,
and at most one update per world tick. Epsilon falls from0.90 to0.08 over the
first80% of training episodes. The saved protocol records all settings and
source hashes before training begins; nonempty output directories are rejected.

## Frozen pilot evaluation

- Training seeds:17,23,41; 600 standard episodes per seed.
- Evaluation worlds:9000000 through9000039, disjoint from hashed training seeds.
- Evaluate standard, long_routes, and scarce_b on identical world seeds across
  all five policies. Do not train on the latter two regimes.
- Deserialize trained and untrained checkpoints before evaluation. No replay,
  optimizer update, parameter selection, or cross-world memory is allowed during
  evaluation. Validate parameter hashes and optimizer counts remain unchanged.
- Primary metric: completed batches by the fixed horizon in the standard regime.
  Secondary metrics: delivered resources, contention denials, inspections,
  travel, final imbalance, in-transit items, and per-type conservation residuals.
- Report paired differences with crossed resampling of training seeds and world
  seeds. Citizens and ticks are not independent experimental repetitions.
- Predeclared pilot learning criterion: mean trained-minus-untrained gain at
  least0.25 batches and crossed-bootstrap interval lower bound above zero.
  Scripted superiority is a separate contrast. These are exploratory pilot
  diagnostics from three training seeds, not confirmatory statistical proof.
- No tuning after viewing these held-out results. Preserve unfavorable runs,
  frozen models, raw episode metrics, protocol, and representative trajectories.

The CI development smoke uses seed101, 40 episodes, four separate worlds starting
at8000000, and standard only. It checks executable/provenance invariants, not
performance or the pilot learning criterion.

## Reproduce

Use Python3.12 and NumPy2.3.5. No API key, LLM, or GPU is required.

```powershell
python -m pip install numpy==2.3.5
python -m unittest discover -s scripts -p "test*colony_task*.py" -v
python scripts/train_colony_task_allocation.py --episodes 600 --training-seeds 17,23,41 --worlds 40 --output-dir run/colony-allocation-v0-4-pilot
```

The output contains a protocol recorded before learning, frozen trained/untrained
models, a report with raw run metrics, and first-world action/event traces.
The branch's CI uploads the corresponding output as an artifact. This does not
install any model into a Minecraft server.

## Required transfer gate

A favorable pilot would justify Python/Java inference parity and a new observed
Forge tensor mapping before any opt-in live policy trial. An unfavorable pilot
should first be diagnosed from trajectories and training coverage. Changing
rewards, observations, seeds, or hyperparameters then requires a new protocol
and fresh held-out worlds.

## Recorded first pilot result

The declared600-episode/three-training-seed pilot was executed without tuning on
its held-out outcomes. Total optimizer updates:114877. All weights changed from
initialization, checkpoints were saved/reloaded before evaluation, and evaluation
left their parameter hashes unchanged. There were1800 policy/world/training-seed
records and zero per-type conservation violations.

Mean completed batches per64-tick episode:

| Evaluation regime | Trained | Untrained | Balanced script | Nearest script | Random |
| --- | ---: | ---: | ---: | ---: | ---: |
| Standard | 2.525 | 0.000 | 3.775 | 3.750 | 1.550 |
| Longer routes | 0.425 | 0.000 | 2.400 | 2.075 | 0.500 |
| Scarce typeB | 1.550 | 0.000 | 2.000 | 2.000 | 1.325 |

The primary standard trained-minus-untrained difference was+2.525 batches, with
descriptive crossed-bootstrap95% interval[2.142,2.925]. Every training seed had
a positive difference (2.425,2.600,2.550), meeting the declared pilot criterion.
The standard trained-minus-random difference was+0.975[0.542,1.442].

The stronger comparison was negative: trained-minus-balanced was-1.250
[-1.658,-0.875] on standard worlds and-1.975[-2.225,-1.700] on longer routes.
Long-route performance was numerically below random, but its difference
interval[-0.325,0.200] does not establish a reliable deficit versus random.
Scarcity also did not establish a reliable improvement over random.

Trajectory diagnosis is suggestive rather than causal: trained workers averaged
54.33 completed inspections in standard worlds, versus13.73 for the balanced
script. Across the three saved first-world standard traces,158 of199 inspection
choices targeted the worker's current site. The corresponding long-route example
count was134 of159. Repeated cheap inspection and weak long-route transfer are
therefore concrete next investigation targets; this pilot does not identify
whether action redundancy, credit assignment, or approximation error causes them.

The model is **not admitted to live Forge control**. This establishes a training
effect and improved standard-world output over untrained/random controls in an
abstract simulator. It does not establish learned interaction-specific
coordination, superiority to simple scripts, communication benefit, emergent
roles, or Minecraft transfer.

Protocol SHA256:
`64b2b0bfc1bc74ce967bfcd753376d13030446419368a8939ed866fcce0b93af`.
Frozen trained parameter hashes for seeds17/23/41:

- `4003ec32f02502a526653c71f14e8ae14ab5ea7fca6bc0fca1bd1c2363a363b8`
- `a7ce709660284e6f410fc90b4c0e7e622f0b474e4bd81a58eb06f66d0f159625`
- `f9fa58b95d76d47f1271920523f8e44d299f5838d5da57cabfece2de692e6295`

Preserve these results. A follow-up should predeclare a comparison that isolates
redundant inspection from temporal credit assignment, keep a strong scripted
control, and allocate new held-out worlds before changing the policy. More
training or an alternate model should not be presented as fixing this failure
until that independent comparison has actually run.
