# Online masked allocation v0.7

This implements the next training intervention after #199: remove the physically
redundant fresh current-site INSPECT action consistently during exploration,
greedy execution and Double-DQN successor selection. WAIT stays legal. This is
online reward learning, with no expert labels, LLM or Minecraft control change.

Compare full versus pruned action design from identical initial weights, world
seeds, reward, features, network and hyperparameters. Train 600 episodes per arm
for seeds 17/23/41. Four initial episodes collect replay without gradients; every
subsequent tick performs one update: exactly 38144 per learner, 228864 total.
Separate exploration and minibatch RNG streams. Replay contents necessarily
change with behavior; this is the total training-time action-design effect,
not a fixed-data backup experiment. Both arms get identical world/tick budgets.

Use fresh evaluation worlds 9200000..9200039 in standard, longer-route and scarce-B
regimes. Save/reload models before evaluation. Record actual updates and verify
frozen weights. The primary standard pruned-minus-full criterion remains mean
gain at least 0.25 batches and crossed-bootstrap interval lower bound above zero.
Balanced scripts remain the practical baseline. Three training seeds permit
exploratory conclusions only. No tuning after looking at these worlds.

The protocol and source hash are saved before learning; nonempty outputs are
rejected. Preserve original v0.4 sources and checkpoints. New saved models include
`online_mask_contract`; raw parameter loading alone does not restore this policy.
Inference must reconstruct MaskedNetwork with the recorded prune boolean, as
the experiment's reload path does. `colony_masked_policy.load_policy` supplies
a strict reusable simulator loader: it rejects missing/incorrect mask types,
incompatible trainer hashes and changed original source contracts. It retains
the saved mask semantics rather than silently interpreting raw weights as an
unmasked actor. No live Minecraft policy loader is installed here.

Tests independently verify that a high-valued removed head cannot enter the
bootstrap target, that WAIT remains available, and that actual optimizer counts
match the declared tick budget. Run:

```powershell
$env:OPENBLAS_NUM_THREADS = "1"
python -m unittest discover -s scripts -p "test*colony*.py" -v
python scripts/train_colony_masked_online.py --episodes 600 --output-dir run/colony-masked-online-v0-7
```

## Completed pilot

All six runs completed: 3600 training episodes, 230400 world ticks and 228864
actual optimizer updates. All 1440 frozen evaluation records reached tick 64,
with zero per-type conservation violations. Strict checkpoint reload preserves
the learned mask. Source hashes match the protocol saved before training.

| Regime | Full action training | Pruned action training | Balanced script | Paired gain (95% descriptive interval) |
| --- | ---: | ---: | ---: | --- |
| Standard | 2.758 | 3.817 | 4.350 | +1.058 [0.517, 1.683] |
| Longer routes | 0.858 | 1.092 | 2.575 | +0.233 [-0.234, 0.734] |
| Scarce typeB | 1.533 | 1.883 | 2.000 | +0.350 [0.175, 0.567] |

The primary standard gain criterion is met, with per-seed gains 1.475, 1.050, 0.650.
The standard mean increases about 38%; the learned actor reaches about 88% of
the balanced script's production on these worlds. The secondary scarcity gain
also meets the numerical criterion. Long-route transfer remains inconclusive.
These comparisons use identical fresh worlds within this experiment; prior
pilot averages used different worlds and should not be compared directly.

This supports consistent training-time action design in this bounded simulator.
It does not establish script superiority, learned communication, emergent roles,
or Minecraft transfer. Keep this model as the learned candidate for subsequent
robustness/inference-parity work; retain scripted live control. Do not select
the best seed or tune on these evaluation worlds. Three seeds limit inference.

58 focused tests and the dedicated online-training CI smoke pass. The Minecraft
foundation independently passed all ten v0.3 acceptance workflows, including
real four-citizen hauling, decision contracts and restart recovery. This Python
38-feature tensor still requires an explicit Forge mapping and inference parity
before a controlled live learned-policy experiment.
