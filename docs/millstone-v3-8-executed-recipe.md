# Hearthbound v3.8 — Create-selected milling recipe

Added the `MillstoneRecipeAccessor` Mixin to read Create 6.0.8's private `lastRecipe` field after its `process()` method completes. The existing HEAD/RETURN mutation observer now logs both:

- `candidateRecipe`: separate Hearthbound pre-processing lookup
- `executedRecipe`: the recipe selected or retained by Create in `lastRecipe` after processing
- `recipeAgreement`: whether these IDs match

This does **not** change Create recipe selection, roll RNG a second time, or award technology research. Important caveat: `lastRecipe` is Create's internal cached recipe; a post-method read alone must not be promoted to a proven executed recipe in the authoritative receipt contract until it is validated against actual processing, including failed/early-return cases. A successful single-item input delta is still the diagnostic event gate. Recipes may match ambiguously, outputs may be stochastic, and slots may be extracted by other automation.

The build's JAR verification now checks the accessor class and Mixin configuration. Next verification is fresh Forge CI, then an EULA-authorized Minecraft server startup and a real milling event. Research credit remains explicitly false.
