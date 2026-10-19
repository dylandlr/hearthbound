# Hearthbound v1.9 — Minecraft simulation harness

This workflow runs **real Minecraft Forge + Create dedicated-server simulations in GitHub Actions**, without requiring the graphical client.

## Running

GitHub Actions > Minecraft simulation harness > Run workflow.

- Scenario: `autonomous-scientist` or `basic-smoke`
- Seed: signed integer, default 42

On push to the feature branch, the default autonomous-scientist scenario runs.

The workflow boots the actual Forge server, waits for ready, runs the appropriate RCON scenario and uploads:
- `simulation-results/server.log`
- `simulation-results/scenario.log`
- `simulation-results/summary.json`
- Minecraft's `run/logs/latest.log` when available.

`summary.json` includes schema version, scenario, seed, timestamp, exit code, pass/fail derived **only from scenario exit code**, and counts of selected physical research/social log events. Counts aren't independent verification of success; the scenario's assertions are authoritative.

## Boundaries and next experiments

Current runner starts one seed/scenario per invocation. It does not launch a graphical Minecraft client, record gameplay video, or supply trained MLP policies. A seed alone does not ensure perfect cross-run determinism because real-time tick scheduling, entity IDs and concurrency can vary. Repeated trials are required.

Next: run several seeds in a matrix, introduce metrics like time-to-discovery and resources consumed (instrumented in-game), and incorporate a visual client/virtual display for authentic gameplay video. This infrastructure complements the high-throughput fast simulator; it is not a replacement for one.
