# Online masked allocation v0.7

This implements the next training intervention after #199: remove the physically
redundant fresh current-site INSPECT action consistently during exploration,
greedy execution and Double-DQN successor selection. WAIT stays legal. This is
online reward learning, with no expert labels, LLM or Minecraft control change.

Compare full versus pruned action design from identical initial weights, world
seeds, reward, features, network and hyperparameters. Train 600 episodes per arm
for seeds17/23/41. Four initial episodes collect replay without gradients; every
subsequent tick performs one update: exactly38144 per learner,228864 total.
Separate exploration and minibatch RNG streams. Replay contents necessarily
change with behavior; this is the total training-time action-design effect,
not a fixed-data backup experiment. Both arms get identical world/tick budgets.

Use fresh evaluation worlds9200000..9200039 in standard, longer-route and scarce-B
regimes. Save/reload models before evaluation. Record actual updates and verify
frozen weights. The primary standard pruned-minus-full criterion remains mean
gain at least0.25 batches and crossed-bootstrap interval lower bound above zero.
Balanced scripts remain the practical baseline. Three training seeds permit
exploratory conclusions only. No tuning after looking at these worlds.

The protocol and source hash are saved before learning; nonempty outputs are
rejected. Preserve original v0.4 sources and checkpoints. New saved models include
`online_mask_contract`; raw parameter loading alone does not restore this policy.
Inference must reconstruct MaskedNetwork with the recorded prune boolean, as
the experiment's reload path does. No live policy loader is installed here.

Tests independently verify that a high-valued removed head cannot enter the
bootstrap target, that WAIT remains available, and that actual optimizer counts
match the declared tick budget. Run:

```powershell
$env:OPENBLAS_NUM_THREADS = "1"
python -m unittest discover -s scripts -p "test*colony*.py" -v
python scripts/train_colony_masked_online.py --episodes 600 --output-dir run/colony-masked-online-v0-7
```
