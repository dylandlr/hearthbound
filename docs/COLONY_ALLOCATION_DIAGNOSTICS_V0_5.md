# Colony allocation diagnostics v0.5

Status: completed abstract-simulator pilot, stacked on PR #197.
The v0.4 environment, trainer and original three checkpoints stay unchanged.
No Minecraft execution or LLM is introduced. The protocol is recorded before
the full run; development smoke outcomes do not select the full-run settings.

## Questions and separate interventions

The v0.4 learned actor repeatedly inspected its current site and remained below
the balanced script. Neither symptom identifies a cause. This experiment asks:

1. Does removing the duplicate local inspection choice improve the **unchanged
   v0.4 weights**? Evaluate full and pruned masks on identical fresh worlds.
2. On a **fixed random-behavior corpus**, does a longer reward backup improve
   learning over one-step Double DQN, holding initialization, sampled starting
   transitions, optimizer count, architecture and all other settings fixed?

These comparisons answer different questions. The offline comparison does not
retroactively explain the original online learner's failure. A full/pruned
cross of the new policies is secondary; there is no training with a pruned mask.

## Action alias contract

An idle worker automatically receives a fresh local stock observation. INSPECT
of that same site consumes one tick without moving or extracting. For that
case its physical state, rewards, next observations and elapsed time match
WAIT. Inspection counters and evaluator event labels differ; they are not
policy inputs. Tests cover positive/empty stock, peer hauling and busy peers.

The inference intervention removes only this fresh current-site INSPECT action
using the published 38 observation features. It keeps WAIT and every other
originally valid action. It reranks the same Q heads instead of forcing a haul,
using hidden stock, or substituting a new controller. Unknown/stale cases are
not pruned. Removing an alias changes which Q estimate wins; improvement would
show that this action-selection intervention helps, not why the estimates arose.

## Fixed replay and backup contract

For each seed 17, 23, 41, generate 300 standard-regime 64-tick episodes with two
workers. Behavior is uniform over the original locally valid action mask and
does not depend on either learner. Preserve the complete corpus and its hash.
Train both arms from identical 38→64→9 initial weights using identical sampled
starting indices and order, batch 32, 12000 Adam updates, rate 0.001, target copy
every 200 updates, Huber loss and gradient norm cap 5 from v0.4. Both arms retain
the original full mask in training.

One arm uses the existing one-option Double-DQN target. The other may extend
through at most five consecutive options of the **same worker and episode**,
including a successor reward only when its recorded action equals the current
online model's greedy action at that observation. At a non-greedy successor,
cut **before** including its reward and bootstrap at its observation. At the
depth limit bootstrap normally; at the episode terminal do not bootstrap.
Validate exact tick/observation continuity at every link. Discount each reward
by accumulated actual ticks, not number of options. For durations 2, 3, 1 and
option returns 1, 2, 4, the combined return is 1 + gamma²×2 + gamma⁵×4, duration 6.

This finite greediness-truncated backup takes the off-policy trace-cutting idea
discussed by [Munos et al. (2016), Safe and Efficient Off-Policy Reinforcement
Learning](https://papers.neurips.cc/paper_files/paper/2016/file/c3992e9a68c5ae12bd18488bc579b30d-Paper.pdf).
It is not Retrace(lambda) and inherits no tabular convergence guarantee for
this partially observed, shared-network multi-agent setup. Naively including
five random-behavior rewards would change the target toward behavior value.
Report actual backup depth and the fraction extending past one; do not call
every sample a five-step return. Extra successor reads are part of the treatment,
so equal optimizer count is not equal compute or equal reward exposure.

The corpus has random teammates; deployment evaluates greedy teammates. This
distribution change and finite coverage can affect both arms. There is no
importance correction for the other worker's policy. No expert labels or
counterfactual hidden outcomes are supplied.

## Frozen evaluation and interpretation

- Use fresh world seeds 9100000..9100039, disjoint from v0.4's 9000000..9000039
  and the current hashed training worlds. Do not tune on these outcomes.
- Evaluate standard, long_routes and scarce_b. Each of three seeds supplies
  legacy_online, offline_td, offline_greedy5 and untrained models. Also run
  balanced, nearest and random controls. Evaluate each with full/pruned masks:
  3×40×3×7×2 = 5040 episode records. Deterministic scripted controls are repeated
  within seed blocks; those repetitions are not independent worlds.
- Load every checkpoint before evaluation. Preserve the original legacy bytes
  and pinned parameter hashes. Check weights and optimizer counters stay fixed.
- Primary alias contrast: legacy pruned minus legacy full, standard regime.
  Primary credit contrast: offline_greedy5 minus offline_td, **full mask**,
  standard regime. Report every seed and all secondary regimes, including losses.
- Primary metric is completed physical batches by tick 64. Record alias choices,
  waits, travel, deliveries, contention and per-type conservation. Alias pruning
  must leave zero current-site inspection selections.
- Descriptive paired crossed-bootstrap 95% intervals resample training and world
  axes. Pilot gain criterion is mean gain ≥0.25 batches and interval lower bound>0.
  Only three training seeds and exploratory follow-up selection preclude a
  confirmatory superiority claim. No multiple-comparison-adjusted testing occurs.
- Strong scripted controls remain the practical comparison. This pilot neither
  establishes learned coordination/communication nor authorizes Minecraft control.

Record source/runtime/protocol hashes before learning, exact corpus hashes,
minibatch-order hashes, actual updates and backup depths, model hashes and raw
paired runs. Reject nonempty output directories. Preserve negative results.

## Reproduce

Python 3.12 and NumPy 2.3.5, no GPU or API key required. Keep the exact original
v0.4 `trained-17.json`, `trained-23.json`, `trained-41.json` in the input directory.

```powershell
python -m pip install numpy==2.3.5
$env:OPENBLAS_NUM_THREADS = "1"
python -m unittest discover -s scripts -p "test*colony*.py" -v
python scripts/colony_allocation_diagnostics.py --legacy-dir run/colony-allocation-v0-4-pilot --output-dir run/colony-diagnostics-v0-5-pilot
```

CI deliberately uses `--skip-legacy`, seed 101, 20 corpus episodes, 60 updates,
four standard worlds starting 8100000. It verifies execution and integrity; it
does not manufacture new weights and label them the original v0.4 checkpoints.
The full pilot requires the pinned originals and reports legacy provenance.

## Recorded pilot result

The declared run completed without changing source, hyperparameters or seeds
after inspecting the held-out outcomes. The fixed corpora contained 37499 option
transitions from 900 episodes (57600 world ticks). Six learners performed 72000
actual optimizer updates in total. Every paired arm shared its initialization
and 384000 sampled start indices, with matching order hashes. All 5040 evaluation
records reached tick 64 with zero per-type conservation residuals. Reloaded
evaluation weights and optimizer counts stayed fixed. Original legacy files
were copied byte-for-byte and their pinned parameter hashes verified.

Mean completed batches per 64-tick episode, **fresh v0.5 evaluation worlds**:

| Regime | Legacy full | Legacy pruned | Balanced script | Nearest script | Random full | Random pruned |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Standard | 2.583 | 2.900 | 3.825 | 3.800 | 1.325 | 1.550 |
| Longer routes | 0.425 | 0.858 | 2.375 | 1.825 | 0.575 | 0.525 |
| Scarce typeB | 1.575 | 1.725 | 2.000 | 2.000 | 1.200 | 1.425 |

The scripts choose no current-site aliases, so their full/pruned outputs match.
Legacy standard gain was +0.317, descriptive crossed-bootstrap 95% interval
[0.000,0.717], with per-training-seed gains [0.175, 0.675, 0.100]. The primary
alias criterion **was not met**, because its interval lower bound is not above
zero. The secondary longer-route gain was +0.433 [0.258, 0.625], positive for all
three seeds. Scarcity gain was +0.150 [0.008, 0.325], below the 0.25 effect threshold.
Alias choices become exactly zero, but WAIT choices increase. Removing this
duplicate action helps numerically and on the secondary long-route contrast;
it does not solve inactivity or close the gap to the strong script.

| Regime | One-step full | Longer-backup full | One-step pruned | Longer-backup pruned | Untrained full/pruned |
| --- | ---: | ---: | ---: | ---: | ---: |
| Standard | 0.533 | 0.817 | 0.683 | 1.075 | 0.000 |
| Longer routes | 0.033 | 0.025 | 0.083 | 0.125 | 0.000 |
| Scarce typeB | 0.383 | 0.533 | 0.450 | 0.675 | 0.000 |

Primary longer-backup minus one-step gain was +0.283 [-0.025, 0.633], with
per-seed gains [0.125, 0.175, 0.550]. This **also missed the primary criterion**.
The secondary pruned-mask credit difference was +0.392 [0.075, 0.775]. These are
not interchangeable contrasts: do not replace an inconclusive full-mask
primary result with a favorable pruned-mask secondary result.

Only 16.76% of longer-backup samples extended beyond one option; mean length was
1.204 options, not five. Both offline learners performed poorly, with output numerically below random, and showed substantial waiting. Standard full-mask WAIT counts
averaged 56.90 (one-step) and 49.06 (longer-backup) per two-worker episode; after
pruning these increased to 103.49 and 93.63. Some waits can be rational at resource
exhaustion or near the horizon, so counts alone do not establish their cause.
This run neither proves that temporal credit is irrelevant nor identifies a
unique cause of offline collapse. Replay coverage, value estimation and the
random-teammate to greedy-teammate shift remain distinct hypotheses.

### Implementation decision

Keep the balanced scripted task selector as the practical control. Keep the
duplicate-inspection mask as a verified simulator intervention; do not describe
it as a complete trained policy fix or install these models into Forge. Do not
scale society/role claims on these allocation results.

Before choosing a new learner, audit frozen Q rankings and replay coverage at
states where the saved agents wait. Separate justified terminal/material-bound
waiting from missed productive opportunities. A subsequent training experiment
must declare whether it changes action design, behavior data or value backup,
hold the others fixed, and reserve new outer evaluation worlds. Training-time
alias removal remains untested here; recurrent memory and additional rewards
would be further interventions rather than established remedies.

Validation: 51 focused tests and the diagnostic CI development experiment passed.
Full pilot protocol SHA256:
`5e073148ec3a332d94f41fcc6803d443be85c36a5bff89b9703a9a3eefd1ef59`.
The evidence bundle preserves raw paired metrics, actual corpora, all new and
legacy input checkpoints, first-world traces and reproduction instructions.
