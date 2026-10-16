# Hearthbound v0.6.4 — opt-in independent study

## What changed
A server villager tick now invokes LibraryAutonomyTick. The component defaults
OFF per citizen. When enabled, the citizen searches every 200 game ticks (UUID
staggered) for a nearby loaded inventory holding a written book, respecting a
600-tick retry cooldown. If the citizen is free, its study priority is nonzero,
and it does not already know the prototype milling topic, LibraryPolicyBridge
offers a verified executable STUDY action to ColonyPolicy and ActionGate. The
existing travel and reading executors then handle physical world work.

Operator commands for nearest villager:
- /hearthbound library priority 1
- /hearthbound library auto on
- /hearthbound library auto off
- /hearthbound library inspect

## Caveats
- No other legal competing jobs are currently presented to the decision policy
  at the automatic decision boundary; study is a single-option decision, not
  colony-wide stochastic work arbitration.
- A written book is presently only a placeholder and its actual content is not
  authenticated. Do not equate its presence with a real Create or Patchouli lesson.
- No global library registry, ownership authorization, visual reading animation,
  UI or true citizen literacy score is connected yet.
- Existing hauling has its own execution ownership and is only respected by
  current explicit active-state checks, not yet a shared persisted task lease.
- Tick selection and Minecraft behavior are not confirmed by compiling or
  running the Forge dedicated server; this change requires smoke testing.
- Automation is off by default to avoid changes to existing Minecraft behavior.

## Acceptance run
Place written book in a chest/barrel near a named test citizen. Set priority 1,
enable auto, verify the NPC navigates and begins reading without an explicit
assign command, and check persistent knowledge. Next verify study priority 0,
hauling active, missing book, player removal during study, restart, and chunk
unload. Confirm it never grants practical Create mastery without mill evidence.
