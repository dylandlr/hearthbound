# Social Teaching Policy v0.6

The research runtime in v0.5 proved physical Create processing, causal research reward and direct social transmission. v0.6 makes technology sharing an agent-selected, LLM-free social task.

## Hierarchy and policy boundary

SOCIAL → TEACH → selected nearby citizen → personally known recipe.

`SocialTeachingPolicy` consumes schema v1 local inputs: cooperation instinct, teacher confidence, local familiarity (per-teacher reputation), urgency, fatigue, student visible, recipe known and student request signal.

Actions: TEACH, DEFER, REST. It deliberately does not read world state itself. Deterministic scores are a scripted baseline for later MLP comparison, not trained behavior.

## Server runtime

`CitizenSocialTeaching.tick` runs at 20-tick observation cadence. It is opt-in:
- `sable auto-teach-on`
- `sable auto-teach-off`

One teaching attempt at most every 100 game ticks; only physically nearby (4-block) line-of-sight Hearthbound citizens are eligible. A teacher must personally know `create:milling/wheat`, and the recipient must not already know it. Knowledge retains provenance through `CitizenTechnologyKnowledge.teach`.

The first runtime adapter intentionally uses neutral placeholders (urgency 0.5, fatigue 0.0) because real physiological/job observation contracts are not yet wired. This is explicitly a limitation, not a claim of rich social agency.

## Gates

- JUnit: version validation, visible-student gating, unknown-recipe refusal, fatigue, and personality differences.
- Real-server smoke: verified Create experiment creates direct knowledge; manual teaching to Iven; autonomous policy-teaching to Moss, with no teaching command; recipient confirms TAUGHT knowledge.
- Still pending: verified Forge compilation and real Create server E2E on this branch.

## Next slice

Wire physiological and colony need observations; replace reputation scalar with memory-informed trust; allow recipe choice among all known recipes and schedule learning requests from students; compare policy against scripted/static and future MLP baselines on held-out seeds.
