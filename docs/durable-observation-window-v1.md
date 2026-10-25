# Durable operation observation windows v1

`DurableObservationWindow` persists an operation's start tick, citizen and machine before execution using the existing checksummed intent store. An end tick is later durably committed under the same operation UUID in an append-only ledger. Reopening storage reconstructs the complete window, refusing to treat a missing completion as success. Retried identical completion is idempotent; conflicting end ticks or citizen identities fail.

The standalone contract tests verify an incomplete window is rejected, a completed window survives reload, duplicate completion does not change state, and conflicting or foreign completions fail.

**Limitations:** end ticks must come from authoritative server observation; this storage class does not know whether actual Create processing happened. The start and end records are in different files and an interrupted completion leaves an explicitly incomplete (quarantined) window. The live Forge GameTest currently exercises only the journal's bounded selector; it has not yet wired durable operation windows to real mutation timestamps. Two actual milling cycles and two independently attributed credits in Minecraft remain outstanding.
