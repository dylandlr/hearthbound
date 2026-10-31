# Citizen supply interruption boundaries v1

The Minecraft GameTest now exercises five explicit recovery decisions: before write-ahead attempt; after attempt but before Create inventory mutation; after Create inventory mutation; after citizen wheat debit; and after completion receipt. All points after journal creation remain blocked without separately verified persistent evidence. This guards the decision contract against accidental blind replay changes.

These are **synthetic interruptions to the decision contract**, not real process kills, disk corruption, or restart injection at the specified tick. The no-replay and saved-world restart experiments remain separate already-passed acceptance tests.

Next implementation needs a test-only, server-tick injected halt boundary, separate fresh fixture worlds per phase, and post-restart inventory counts against write-ahead receipts. Avoid using this synthetic test to claim crash-atomic or exactly-once execution.
