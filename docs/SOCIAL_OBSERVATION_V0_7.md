# Social Observation v0.7 — citizen learning requests

This incremental slice adds per-citizen requests to the existing LLM-free social teaching system. It does not pretend that hunger, fatigue, kinship, or mature trust graphs are implemented.

## Contracts

- A citizen can request an unfamiliar recipe via `sable learning-request "<recipeId>"` executed as that citizen.
- Requests are persisted in that citizen's own Minecraft entity NBT (`hearthbound.learningRequestV1`).
- `sable learning-request-inspect` reports the selected citizen's request.
- A teacher's social executor only considers students within 4 blocks and direct line of sight.
- A local student's request changes the policy observation (`studentRequestsLearning=true`, urgency proxy 0.8), and requesting students are considered before nonrequesting students.
- A successfully taught recipe clears the matching student's request.
- No global recipe list is unlocked; the recipient still gains a provenance-bearing `TAUGHT` knowledge entry.

## Limitations

`CitizenSocialTeaching` still demonstrates wheat milling only. Fatigue is intentionally a neutral placeholder because Minecraft villagers do not have an authoritative hunger/fatigue metric. The request is explicit through a server command, not yet an independently selected learner policy action. Knowledge transmission still uses existing `CitizenTechnologyKnowledge` validation.

## Acceptance

Extend the physical Create First Mill smoke scenario: after Sable earns the milling recipe, Moss requests it; autonomous teaching must transmit it and clear Moss's request. Preserve previous reservation, taint and event provenance negative controls.

## Next

Make request formulation learner-selectable, broaden candidate recipes, and bind physiological needs and task urgency to real measured sensors before claiming socially adaptive emergent agents.
