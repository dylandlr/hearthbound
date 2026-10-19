# Hearthbound v2.1 — Measured Research Latency and Resource Use

Adds per-scenario `metrics.json` to the real Minecraft autonomous-scientist acceptance script and carries it into the existing `summary.json` reports through `--metrics`.

Measurements are collected from actual RCON-observed milestones using `time.monotonic()`:
- `seconds_to_proposal`: elapsed wall time after auto-research is enabled until proposal + physical job are observed
- `seconds_to_haul`: time until the citizen's hauling job is reported complete
- `seconds_to_first_flour`: time until the actual Create mill reports its first flour
- `seconds_to_confirmation`: time until the verified receipt, reward, learned technology and confirmed hypothesis have all been asserted
- `wheat_consumed`: one unit, checked by physical source inventory assertion

These are **wall-clock timings**, not Minecraft tick latencies, and depend on runner speed. They should not be compared across differently provisioned hardware as if they were simulation ticks. Missing metrics remain `null` in the summary; a failed scenario must not manufacture positive results.

The generic smoke workflow is still sometimes red due to an immediate citizen proximity assertion after wheat delivery, and this was observed in the parent v2.0 branch. It remains a separate validation issue rather than proof of a research latency regression.

Next measurement improvement: instrument server game ticks at milestones, persist partial failure metrics, and compare different policy baselines across the same seeds.