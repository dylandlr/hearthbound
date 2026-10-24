# Hearthbound v3.7 — Milling Recipe Candidate

The Create millstone mutation audit resolves a **candidate milling recipe** immediately before Create's private `process()` call by invoking `AllRecipeTypes.MILLING.find(new RecipeWrapper(millstone.inputInv), level)` on the server. The log field is `candidateRecipe`. If no match is found, it is `unresolved`.

This is intentionally **not** labeled an authoritative executed recipe. Create caches `lastRecipe` internally; Hearthbound's separate lookup can differ if more than one recipe matches or the cache differs. Actual recipe proof would need the exact recipe used by the executed Create method, without rerolling outputs or changing Create behavior.

**Safety:** observations still have `researchCredit=false`. Neither a candidate ID nor end-state deltas can satisfy the durable `MillstoneReceiptGate` contract on their own.

Verification requirements:
- Compile and package latest candidate lookup; verify Mixin injection on an actual server.
- Validate one wheat processing operation; inspect `candidateRecipe`, inventory mutation and server tick.
- Test conflicting matching recipes, missing recipe, recipe changes on datapack reload, and output extraction.
- Only then implement authoritative receipt persistence and citizen credit.
