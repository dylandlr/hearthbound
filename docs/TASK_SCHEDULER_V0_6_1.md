# Hearthbound shared task scheduler v0.6.1

CitizenTaskArbiter is a minimal, dependency-free task ownership contract,
with unique lease IDs, exclusive active task, strict owner releases, and a
restore operation for reconstructing assignments on world load.

These tests define safety before integrating movement and Create machinery.
It is NOT yet wired to all Minecraft job owners and does not persist leases
by itself. Before enforcing it at runtime, migrate hauling and experiment
assignments to the same owner and reconcile leases after server restart.

Hierarchy: policy chooses high-level action; scheduler arbitrates ownership;
executor performs navigation and physical actions; server checks evidence;
learning system consumes verified outcome.

Acceptance requirements for integration:
- No concurrent haul/study navigation for one citizen.
- Stale completions cannot cancel newer tasks.
- Study timeout and book removal release ownership.
- Save/restart restores task ownership once.
- A physical Create process, not a book, establishes practical mastery.
- MLP consumes the same observation schema as the scripted baseline.
