# Restart journal compatibility fix

The Minecraft server smoke run 40224796328 failed after successful GameTests: the restart validator expected exactly one milling observation, although the new consecutive-milling GameTest produces additional genuine Create events. That check conflated an earlier checkpoint with the complete later journal and crashed the restarted server.

The restart validator now requires three persisted real Create events and verifies that **every** observation captured in the earlier checkpoint survives unchanged by UUID. It still tests duplicate append, conflicting duplicate rejection and all original receipt/credit/machine checkpoint invariants. This deliberately allows later real operations without weakening the identity of earlier evidence.

The latest visible citizen GameTest also remains part of the server acceptance suite. Neither this repair nor the visible villager establishes learned autonomous actions.
