# Core test execution record — 2026-10-14

## Local environment
- Runtime: OpenJDK 21.0.12.1 compiler, targeting `--release 17`.
- Repo reference: `feature/first-mill-foundation` at smoke-test revision around `dd66605` and later test changes.
- GitHub direct clone unavailable in local runtime; sources were retrieved through GitHub connector.
- The two more recent policy-boundary and randomized-ledger test classes were run as retrieved. Three earlier smoke-test classes were reconstructed with the same primary scenarios for local verification, **not byte-for-byte source reproductions**.
- Five standalone test programs passed locally, including 20,000 randomized transfer sequences.
- Do not treat these as a green GitHub CI run, JUnit result, Forge build, Minecraft GameTest, or E2E run.

## Still blocked
GitHub Actions job reports failure with empty job step summaries and no assigned runner; fetching its archived job logs returns BlobNotFound. Need inspect repo Actions UI and account/org runner eligibility. A working JDK is insufficient to compile Forge without ForgeGradle/MDK dependencies and wrapper.

## Required next checks
1. Exact-source suite: obtain byte-for-byte clone/check out and run `bash scripts/test-core.sh`.
2. Provision Gradle wrapper from official Forge MDK and run `./gradlew test build`.
3. Introduce Minecraft GameTests and real server/client run with Create.
4. Verify restart-safe item accounting; current entity NBT/world save protocol is not crash-atomic.
