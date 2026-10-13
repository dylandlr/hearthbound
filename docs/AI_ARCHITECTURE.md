# Swappable Colony Intelligence Architecture

## Separation of responsibilities
Minecraft server owns state and validates changes. Citizens use identical observation schemas and bounded action choices regardless of intelligence backend. The action executor handles inventory reservations, pathing, execution, failure and persistence.

## Policy interface
Input: snapshot id, agent id, observations (jobs, needs, inventory, accessible stations, local hazards, skills, relationships), available_actions, and deadline.
Output: action id, type, typed arguments, expected state version, optional justification.
All outputs are validated; invalid/stale/duplicate actions are rejected.

## Controllers
- B0: priority rules + utility scoring (deterministic and interpretable).
- B1: decision tree trained by imitation from scripted expert or recorded players.
- B2: random forest trained on identical tabular demonstrations.
- B3: small MLP/neural network over fixed observations.
- B4: RL policy trained in a fast deterministic simulation using explicit rewards.
- B5: LLM deciding selected high-level intentions with strict schema and bounded inference budgets.
- Hybrid: rule-based reflexes and execution, ML scheduling, selectively invoked LLM social/strategic planning.

Decision trees, forests, and neural models do not learn online merely because their predictions change. Experiment manifests must specify training data, model version, evaluation seeds, and whether updates occur during a run.

## Safety and reliability
No model can spawn items, mutate the world outside the server action executor, bypass permissions, or execute arbitrary generated code. Use idempotent tasks, item reservations, timeouts and crash recovery. Model failure falls back to deterministic safe behavior.

## Boundary for actual Minecraft testing
A headless policy benchmark is a supplement only. Main acceptance requires actual Create blocks, real inventories, persistent NPCs and a Minecraft client/server playtest. Do not label animation or rendered mockups as Minecraft gameplay.
