# Hearthbound v0.7.7 — build coverage and physical offer preflight

## CI repaired
The existing `.github/workflows/forge-compile.yml` was scoped to older
development branches and did not include `feat/emergent-tech-evidence-v0-4`.
Its push filter now covers `main`, `feat/**`, and `fix/**`.
`workflow_dispatch` is enabled for manual triggering. It continues to use
Temurin Java 17 and Gradle 8.8, and now runs `compileJava --stacktrace`.

The repository currently does not include `gradlew` or Gradle wrapper files,
so the GitHub workflow installs a pinned Gradle release. A workflow run has
not been confirmed passing; this is CI configuration, NOT a verified Forge
build. Container Git operations cannot resolve github.com.

## Read-only offer preflight
`SableHauling.hasAvailableWheat(level, source)` reads existing inventory
counts without removing or reserving items. It returns false for an unloaded,
unsupported, or empty source. `SableWorkChoice` now requires it when creating
a hauling offer. This prevents an empty source from being accepted as an
apparently executable job simply because its chunk is loaded.

The check does NOT guarantee that the destination can receive the wheat,
that the source is still stocked by pickup time, or that pathfinding succeeds.
The executor still owns inventory mutation, claims, and cargo quarantine.

## Executed checks
Locally compiled Java 17-compatible reproductions of the checked-in
`WorkOfferLifecycle` and `WorkOfferLifecycleTest` source logic and ran the
12 lifecycle assertions: **12 checks passed**.

## Further acceptance gates
1. Confirm successful GitHub Forge workflow and identify any compile errors.
2. Spawn Sable with an empty source and valid primer; work-choice must
   mark HAUL unavailable without assigning a paused haul.
3. Add wheat and repeat; HAUL should be considered if enabled.
4. Verify successful pickup, delivery, source claim release, and receipt.
5. Verify verified-completion gate allows study after haul, including
   save/restart and cargo quarantine cases.
6. Check no item loss or duplication in Minecraft.
