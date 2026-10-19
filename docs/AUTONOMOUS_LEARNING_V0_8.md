# Autonomous Learner Initiative v0.8

## Change

Learners can now choose to request `create:milling/wheat` through an LLM-free student-side baseline instead of requiring a player/admin command.

`LearningRequestPolicy` v1 selects REQUEST/DEFER from curiosity, unknown-recipe confidence, local need proxy, visibility of a teacher advertising the recipe, existing request, and personal known state. A student cannot initiate a request for a known recipe or a teacher they cannot observe.

`CitizenLearningInitiative` is opt-in with `sable auto-learn-on` and `sable auto-learn-off`. Each consideration is throttled to one per 100 server ticks. Advertised teaching currently means an opt-in nearby Hearthbound teacher who knows wheat milling and is physically visible within four blocks.

## Limitations

This is a **deterministic, scripted baseline**, not trained ML. A student's teacher lookup checks the teacher's known recipe as an approximation of an explicit locally visible teaching offer; future message-based advertisement must replace that shortcut. Student need is currently a proxy (0.6). The full recipe catalog and legitimate physiological hunger/fatigue observations are not yet wired. This should not be represented as full autonomous curiosity or generic scientific discovery.

## Gates

Four JUnit tests verify request, privacy/visibility gating, known-recipe gating, duplicate prevention, reluctance, and invalid schema. The Create end-to-end script now also spawns Nia with auto learning enabled, requires taught milling knowledge, and verifies request cleanup. To prove **request before teaching** beyond end-state, add event-log/counter checks (the current smoke only tests eventual taught knowledge and cleared requests).

Keep PR as draft until relevant Forge and real-server runs succeed.
