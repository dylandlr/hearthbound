# Hearthbound library policy bridge v0.6.3

Connects per-villager priority (NBT, 0=off; 1 highest to 4 lowest)
to existing ColonyPolicy, StochasticPriorityPolicy, ActionGate and
AutonomousLibraryStudy. It exposes only a real available study job and
revalidates execution in the existing movement executor.

This is a **limited vertical slice**, not automatic autonomous work selection.
It intentionally does not manufacture EAT, FLEE, HAUL or IDLE candidates
for which the scheduler has no valid server task. Live needs are not yet
provided to the policy adapter. The full scheduler must observe and gate
all task candidates, enforce exclusive task ownership across hauling and
study, and choose work when the current task completes.

Use LibraryPolicyBridge.setStudyPriority(villager, 0..4) from the
command/UI, then consider(serverLevel, villager, shelf) at a real
decision boundary. Current written-book authentication remains a
separate priority before general game exposure.

Do not claim this branch is compiled or gameplay-verified.
