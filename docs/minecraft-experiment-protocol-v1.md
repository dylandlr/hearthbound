# Minecraft experiment protocol v1

## Purpose
Convert a Forge build into a reproducible, inspectable Minecraft runtime experiment. Never equate Java contract tests, Forge compilation, or a packaged JAR with a gameplay pass.

## Run identities and provenance
The dedicated-server smoke workflow records the immutable GitHub run ID, attempt number, commit SHA and ref. Its artifact name embeds run ID and attempt. `evidence/manifest.json` stores SHA-256 hashes and counts of expected runtime markers for `gametest.log` and `server-smoke.log`. Artifacts are retained for 30 days. The GitHub Actions summary links to the run and its evidence; preserve the ZIP externally for long-term research.

## Run discovery
Every completed or failed smoke job writes its run identifier and artifact name as a comment to [experiment index issue #77](https://github.com/dylandlr/hearthbound/issues/77), using the workflow GITHUB_TOKEN with issues:write. This closes the gap where the available GitHub integration can read a known run ID but cannot list every workflow run. If that post fails, the run itself is marked unsuccessful and the GitHub Actions summary is the fallback. The index tracks run locations, not pass/fail verdicts.

## Execution
- EULA acceptance required: manual workflow dispatch Boolean, or deliberately marked feature-branch commit `[eula-accepted-smoke]` with the repository variable not equal to `false`.
- Each smoke attempt runs GameTests in a Forge game server and then restarts the saved world with a normal Forge server. CI uses Java 17 and Gradle 8.8.
- Experiment is single-flight (concurrency group), avoiding overlapping runs with potentially confusing evidence.
- `scripts/verify_gametest_log.py` fails closed if any required fixture marker or milling mutation evidence is absent. The restart checker requires journal, machine/intent and discovery markers.
- The evidence packager runs even if earlier steps fail; the artifact uploads with `if: always()` and includes available logs and manifest.

## Evidence interpretation
- `gameplay_markers_observed` and `restart_markers_observed` only report required marker presence, **not** overall success.
- `verified_runtime` also requires the CI job to report success; examine the run conclusion and job steps directly. A failure after the packager can still invalidate the final job, so do not rely exclusively on this field.
- Diagnostic logs are not a synchronized video recording. No screenshot or POV video is captured by this protocol.
- No claim that AI citizens autonomously learned may be made from milling fixtures alone.

## Acceptance to advance gameplay
1. The dedicated-server workflow exists in Actions with an identifiable, completed run.
2. GameTests complete without fixture or process failures.
3. Real Create milling yields a single qualified server-observed operation.
4. A fresh server process reloads the same operation and discovery exactly once.
5. The run's complete artifact is retrieved and retained by SHA-256.

## Research extension
After one verified smoke, add a versioned run specification (Minecraft/modpack versions, seeds, agent policy hash, reward schema, action/observation schema, trial duration), controlled baselines, and synchronized playback. Repeated seeded trials and outcome attribution are essential before describing agent learning as emergent.
