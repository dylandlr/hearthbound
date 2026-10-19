# Hearthbound v1.2 — Hypotheses linked to verified Create receipts

This increment wires persistent scientific hypotheses into the existing physical Create wheat-milling callback.

**Commands:** `sable hypothesis-mill-propose "<expectedOutput>"` and `sable hypothesis-mill-inspect`. Invoke as the selected citizen (for example `execute as @e[type=minecraft:villager,name=Sable,limit=1] at @s run sable hypothesis-mill-inspect`).

**Verification path:** The experiment must first produce an authorized Create mill processing receipt from an exclusive reserved machine. `TechnologyHypothesisSavedData.observeMillReceipt` requests `MillProcessReceipts.requireVerifiedReceipt` and constructs a journal evidence record with the measured input/output deltas. The stored hypothesis then evaluates its predicted machine/input/output. Unknown or absent hypotheses do not earn special credit.

**Separation:** This adds research interpretation after physical processing, not a new source of rewards. Research award logic remains separately evidence-gated. Hypothesis proposal alone cannot unlock a recipe.

**Acceptance:** The existing real-server First Mill RCON test now proposes wheat→flour before the haul and requires `HYPOTHESIS CONFIRMED` after the direct Create processing receipt. Existing taint, conflicting-job, and replay adversarial controls remain.

**Limitations:** The physical adapter currently handles one known recipe (wheat milling) and tests only a correct prediction in-game. Persisted hypotheses are per-dimension world SavedData, but dedicated restart verification for the new hypothesis record must still be added. The code is a research state transition, not autonomous choice of experimental materials or a trainable learning policy. An internal in-memory journal is reconstructed from the authenticated receipt, not a general persistent research event archive.
