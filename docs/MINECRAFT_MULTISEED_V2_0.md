# Multi-seed Minecraft benchmark v2.0

GitHub Actions `Minecraft multi-seed benchmark` runs **three independent real Forge + Create dedicated servers** using world seeds 11, 42, and 73. On workflow_dispatch choose `autonomous-scientist` or `basic-smoke`. On branch push the autonomous scientist scenario runs by default.

Each job uploads `simulation-results/summary.json`, authoritative server logs, and the scenario transcript as an artifact, even when the scenario fails. The final aggregator downloads all `minecraft-seed-*` artifacts, requires exactly three structurally valid summaries, and generates `benchmark/aggregate.json`.

The aggregate contains success fraction, seed identity, per-event mean counts, and each original per-seed record. Failed trials remain in the report: their results are not hidden by the aggregation. An absent artifact causes the aggregation step to fail, rather than silently reporting a subset.

## Methodological limitations

This is a three-seed integration benchmark, not large-scale RL training. Time and agent scheduling inside Minecraft can vary across runs even with the same seed, so repeat trials are needed for statistically meaningful conclusions. The metric counts are derived from real server log messages and are not a substitute for validating gameplay assertions. The `autonomous-scientist` scenario is still limited to wheat milling. This workflow does not start a graphical client or record video.

## Next

Add event timestamps for discovery latency and conserved inventories, policy-model input selection, and multi-seed confidence intervals. Resolve any failed autonomous scientist scenarios before making claims about completed autonomous discovery.
