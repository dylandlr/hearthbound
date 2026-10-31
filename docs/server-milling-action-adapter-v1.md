# Server milling action adapter v1

This slice moves actual wheat through a server-side primitive instead of constructing the powered GameTest millstone preloaded. The scripted work loop requests SUPPLY_WHEAT; ServerMillingActions transfers one wheat from a server-owned ItemStack into the Create input inventory, shrinks that input by one, and rejects duplicate loading when the millstone slot is occupied. The GameTest then creates a durable operation intent, prepares its fixed citizen assignment, and proceeds with Create motor activation, outcome journaling, credit and restart assertions.

The fixture's held stack is not yet attached to a persistent NPC inventory or a navigable entity. The server adapter has no independent proof of task authorization: only the calling fixture supplies that guarantee. Production integration must pass persisted work assignment authorization and a genuine citizen inventory capability before using the mutation primitive. Do not interpret this as autonomous play.

Acceptance requires a real Minecraft log containing exactly one `HEARTHBOUND_SCRIPTED_WORK_LOOP action=SUPPLY_WHEAT conserved=true`, one motor-activation decision, one milling mutation, and the existing credit/restart markers.
