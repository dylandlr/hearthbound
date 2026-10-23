# Minecraft runtime acceptance

Run `gradle --no-daemon runGameTestServer`, then run
`python scripts/verify_gametest_log.py gametest.log` on captured console output.
The existing dedicated-server workflow now runs both, subject to its existing
Minecraft EULA acceptance condition. The Gradle exit code must also be zero.

Three required fixtures execute: eight inventory identity assertions, 200 ticks
of unpowered milling, and one wheat processed with fixture-supplied rotation.
The last fixture waits 280 ticks and requires one to three flour and at most one seed, matching Create's per-item random bonus rolls. Create's normal
world ticker executes the recipe; the test never calls process() or the audit.
The log verifier requires all three named pass markers and exactly one positive
wheat-to-flour mutation event across this isolated suite, so a missing Mixin,
zero tests, or duplicate hook events fail acceptance.

Scope: setSpeed(256) supplies rotation directly. This tests recipe processing
and the hook, not a real kinetic network. No persistent receipts or research
rewards are enabled. A packaged-JAR server test and a mechanical power fixture
remain separate acceptance milestones. Compilation/runtime results must be
reported independently; adding these tests does not establish that they pass.
