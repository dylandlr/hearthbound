# v0.8.11 — Separate Forge dependency readiness from Minecraft world boot

A paired policy trial has two infrastructure phases: (1) resolving the Forge/Create Gradle userdev runtime and compiling source, and (2) actually booting a Minecraft dedicated server. Earlier CI jobs exhausted the 8-minute startup window while Gradle was still configuring dependencies, before any game began.

The CI matrix now performs a `gradle --no-daemon classes` preflight **before** starting the server clock, with at most three bounded attempts to accommodate transient third-party Maven timeout errors. All failed attempts print diagnostics; a third failure terminates the job with `FORGE_DEPENDENCY_OR_COMPILATION_FAILURE`, not a gameplay verdict. Successful compilation emits `FORGE_PREFLIGHT_SUCCESS`. The job has a 45-minute budget, and the unchanged readiness checks still require an actual Minecraft `Done` line plus Hearthbound initialization. The preflight log is attached as an artifact.

A passing preflight or previous Java-only parity suite is never considered evidence of a Minecraft policy task. This run still requires genuine policy dispatch, physical wheat-to-flour production, Sable experience attribution, per-trial game ticks, paired policy observations and restart persistence.

The two arms use the same terrain seed and fixture but separate worlds; Minecraft RNG and scheduling are not guaranteed paired. A single run cannot establish neural superiority, generalization or reinforcement learning.
