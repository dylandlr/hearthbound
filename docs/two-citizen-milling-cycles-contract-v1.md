# Two-citizen milling credit isolation contract

`TwoCitizenMillingCycleTest` exercises one machine across two **synthetic evidence** cycles and verifies that durable machine handoff preserves exclusive ownership, distinct operation IDs and distinct citizen credits. It also checks replay idempotence, foreign-beneficiary receipt conflicts and restart reopening of both ledgers. This test is not evidence that Minecraft actually executed two milling mutations.

The current Minecraft experiment is a **single real Create wheat operation followed by transfer of machine ownership to a second fixture citizen**. The new test closes a necessary identity/credit-isolation contract before a second real Create operation is introduced.

**Important caveat:** this pure-Java test passes a trusted retirement eligibility decision directly; it is not independent proof of a legitimate machine receipt. Production handoff needs the authoritative gate, claim reconciliation and server event stream. The immediate next GameTest milestone is two actual Create milling mutations in sequence, each bound to its own durable operation and citizen, followed by a server restart proving both balances and machine state.
