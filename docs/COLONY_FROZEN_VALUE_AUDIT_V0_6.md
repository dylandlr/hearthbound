# Frozen allocation value audit v0.6

This exploratory audit follows #198 without training or modifying any model.
It reuses the first four v0.5 worlds (9100000..9100003) in all three regimes,
for seeds 17, 23, 41, three learned policies and both inference masks: 216
episodes. These are selected diagnostic cases, not independent outer holdouts.

For each worker, select its first WAIT with at least 16 ticks remaining, below
the evaluator's material upper bound, where the equal-information balanced
script suggests another valid option. Clone the full simulator state twice.
One branch keeps all simultaneous choices; the other changes only that worker's
current action. Both branches then resume the same frozen team policy until
tick64. Original trajectories, weights and optimizer counts remain unchanged.
The material bound is evaluator-only and does not enter either action selector.
Two selected workers in an episode yield separate branches, not a combined fix.

| Policy | Mask | Selected waits | Better output | Worse output | Same output |
| --- | --- | ---: | ---: | ---: | ---: |
| Original online | Full | 32 | 8 | 2 | 22 |
| Original online | Pruned | 35 | 15 | 1 | 19 |
| Offline one-step | Full | 58 | 15 | 0 | 43 |
| Offline one-step | Pruned | 68 | 21 | 0 | 47 |
| Offline longer backup | Full | 63 | 9 | 2 | 52 |
| Offline longer backup | Pruned | 66 | 11 | 2 | 53 |

Across 322 selected waits, 79 interventions improved output, 7 harmed it and
236 left it unchanged. This establishes missed opportunities in the tested
simulator states. It does not establish that substituting the script everywhere
would improve an entire policy, or that all unchanged waits were rational.
Selected states and multiple workers within an episode are dependent samples;
no inferential confidence interval or population success rate is claimed.

The raw record includes Q(WAIT), Q(alternative), paired final production and
counts of replay actions in a coarse observable context. The context includes
current site/hub, time quartile, public buffer/transit balance sign and known
positive sites. It omits distances and precise quantities, so matching counts
are only a coverage proxy, not proof of support for the exact state. The v0.5
corpus is the actual training data for the offline arms; for the original online
model it is merely a reference corpus, not its training history.

Keep WAIT legal and retain scripted control. The next training design should
measure action-value error on paired diagnostic states and distinguish exact
coverage gaps from incorrect ranking despite observed alternatives. Do not add
a blanket no-WAIT rule or claim replay absence as the unique cause. Any policy
chosen using these cases requires new evaluation worlds.

Raw observations of the audit are in
[data/colony-frozen-values-v0-6.json](data/colony-frozen-values-v0-6.json).
The source hash and sampling protocol were recorded before the audit ran.
All counterfactual rollouts enforce per-type conservation. Three new tests check
branch isolation, deterministic continuation and observation-only context keys.

```powershell
$env:OPENBLAS_NUM_THREADS = "1"
python -m unittest discover -s scripts -p "test*colony*.py" -v
python scripts/audit_colony_frozen_values.py --evidence-dir run/colony-diagnostics-v0-5-pilot --output run/colony-frozen-values-v0-6-reproduction/audit.json
```

The input directory is the extracted v0.5 evidence bundle. Output files cannot
replace an existing audit. No Minecraft control or learned-model promotion occurs.
