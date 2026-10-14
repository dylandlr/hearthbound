# Testing Infrastructure v1 — Actual Evidence and Gates

## Current coverage
- `bash scripts/test-core.sh`: fail-fast, dependency-free Java 17 smoke checks for policy, travel and transfer ledger.
- `src/test/java/dev/hearthbound/jobs/FirstMillCoreTest.java`: JUnit 5 regression tests with named assertions. Requires a provisioned ForgeGradle toolchain to execute with `./gradlew test`.
- `.github/workflows/policy-smoke.yml`: GitHub Actions shell smoke step. A configured workflow is not proof that the runner executed it.
- **No passing automated run recorded at this milestone**, and no Forge integration, Create or Minecraft E2E tests yet.
- The Gradle wrapper and verified Forge build still need to be established. Do not merge on green pure-Java tests alone.

## Mandatory CI gates
1. `bash scripts/test-core.sh` succeeds on fresh Java 17.
2. `./gradlew --no-daemon test` succeeds, JUnit report saved.
3. `./gradlew --no-daemon build` succeeds with the locked Forge dev dependencies.
4. Forge dedicated server startup succeeds.
5. Minecraft/Forge GameTests run: entity spawn; travel; real barrel transfer; blockage; recovery.
6. Create-included test world validates physical powered millstone and real recipe outputs.
7. Two-player server acceptance: no split-brain jobs or item duplication.
8. Actual Minecraft client screen capture of acceptance scenario.

## Required scenarios before claiming safe cargo handling
- Baseline four-wheat transfer preserves source + cargo + destination totals.
- Concurrent assignments cannot claim the same inventory twice.
- Output full after withdrawal retains all carried cargo.
- Stalled, unreachable, broken barrel and unloaded chunk never delete cargo.
- Server stop/restart before/after withdrawal and before/after delivery reconciles stored item counts.
- Crash between barrel save and villager save requires journal or equivalent atomic protocol; current prototype is **not safe** for this.
- Sable death, despawn, and operator disconnect must not destroy cargo.

## CI infrastructure troubleshooting
Actions jobs previously failed in seconds with zero executed steps. Check repository Actions settings, runner availability/allowlist, billable minutes, required permissions or account limits in the GitHub UI. A job that never starts is not a Java test failure. Record the exact GitHub annotations, not guesses.

## Workflow discipline
PR stays draft until checks are demonstrably passing. Never equate unit tests with Forge/GameTest/E2E coverage; keep provenance for video and release artifacts.
