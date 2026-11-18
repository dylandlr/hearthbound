# Colony allocation diagnostics v0.5

Status: fixed protocol for an abstract-simulator pilot, stacked on PR #197.
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

For each seed 17,23,41, generate 300 standard-regime 64-tick episodes with two
workers. Behavior is uniform over the original locally valid action mask and
does not depend on either learner. Preserve the complete corpus and its hash.
Train both arms from identical 38→64→9 initial weights using identical sampled
starting indices and order, batch32, 12000 Adam updates, rate0.001, target copy
every200 updates, Huber loss and gradient norm cap5 from v0.4. Both arms retain
the original full mask in training.

One arm uses the existing one-option Double-DQN target. The other may extend
through at most five consecutive options of the **same worker and episode**,
including a successor reward only when its recorded action equals the current
online model's greedy action at that observation. At a non-greedy successor,
cut **before** including its reward and bootstrap at its observation. At the
depth limit bootstrap normally; at the episode terminal do not bootstrap.
Validate exact tick/observation continuity at every link. Discount each reward
by accumulated actual ticks, not number of options. For durations2,3,1 and
option returns1,2,4, the combined return is1 + gamma²×2 + gamma⁵×4, duration6.

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

- Use fresh world seeds9100000..9100039, disjoint from v0.4's9000000..9000039
  and the current hashed training worlds. Do not tune on these outcomes.
- Evaluate standard, long_routes and scarce_b. Each of three seeds supplies
  legacy_online, offline_td, offline_greedy5 and untrained models. Also run
  balanced, nearest and random controls. Evaluate each with full/pruned masks:
  3×40×3×7×2 =5040 episode records. Deterministic scripted controls are repeated
  within seed blocks; those repetitions are not independent worlds.
- Load every checkpoint before evaluation. Preserve the original legacy bytes
  and pinned parameter hashes. Check weights and optimizer counters stay fixed.
- Primary alias contrast: legacy pruned minus legacy full, standard regime.
  Primary credit contrast: offline_greedy5 minus offline_td, **full mask**,
  standard regime. Report every seed and all secondary regimes, including losses.
- Primary metric is completed physical batches by tick64. Record alias choices,
  waits, travel, deliveries, contention and per-type conservation. Alias pruning
  must leave zero current-site inspection selections.
- Descriptive paired crossed-bootstrap95% intervals resample training and world
  axes. Pilot gain criterion is mean gain≥0.25 batches and interval lower bound>0.
  Only three training seeds and exploratory follow-up selection preclude a
  confirmatory superiority claim. No multiple-comparison-adjusted testing occurs.
- Strong scripted controls remain the practical comparison. This pilot neither
  establishes learned coordination/communication nor authorizes Minecraft control.

Record source/runtime/protocol hashes before learning, exact corpus hashes,
minibatch-order hashes, actual updates and backup depths, model hashes and raw
paired runs. Reject nonempty output directories. Preserve negative results.

## Reproduce

Python3.12 and NumPy2.3.5, no GPU or API key required. Keep the exact original
v0.4 `trained-17.json`, `trained-23.json`, `trained-41.json` in the input directory.

```powershell
python -m pip install numpy==2.3.5
$env:OPENBLAS_NUM_THREADS = "1"
python -m unittest discover -s scripts -p "test*colony*.py" -v
python scripts/colony_allocation_diagnostics.py --legacy-dir run/colony-allocation-v0-4-pilot --output-dir run/colony-diagnostics-v0-5-pilot
```

CI deliberately uses `--skip-legacy`, seed101, 20 corpus episodes, 60 updates,
four standard worlds starting8100000. It verifies execution and integrity; it
does not manufacture new weights and label them the original v0.4 checkpoints.
The full pilot requires the pinned originals and reports legacy provenance.
