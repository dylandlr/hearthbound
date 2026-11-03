# Hearthbound v0.9.6 — Cross-runtime neural Q inference parity

## Starting point

The v0.9.5 neural Q trainer passed its isolated simulator CI. With 300 simulated training episodes and 80 held-out episodes, the neural model and scripted reference each completed 77/80 tasks (96.25%), while an untrained network completed 34/80 (42.5%). No performance advantage against the scripted policy was demonstrated. The neural model received reward-based weight updates, but **only in a toy simulator**.

The v0.9.5 Forge compile/JAR jobs subsequently encountered a third-party Maven PKIX SSL handshake/certificate failure when fetching Create/Flywheel artifacts. That does not demonstrate a neural algorithm defect, but the live Minecraft pipeline must be green before claiming v0.9.5 end-to-end acceptance.

## Parity contract

A new simulator-only export reads the checksum-validated neural checkpoint, serializes 10→20→3 network weights and the exact v2 feature/action order, and generates 48 deterministic Python Q-score/action fixtures covering UNKNOWN, EMPTY, AVAILABLE, stale knowledge, busy, unpowered, processing and output-ready states plus 40 additional randomized feature vectors.

A **separately implemented** Java 17 evaluator reads the exported model, enforces architecture, feature ordering, action ordering and checkpoint provenance, computes all Q-scores, and asserts each differs from the Python reference by at most 1e-9. It also checks every argmax action. The GitHub Actions job deliberately uses plain Java compilation without Forge/Create/Gradle dependencies.

## Important limits

Passing parity proves **numerical agreement**, not Minecraft policy suitability, correctness of environment dynamics, safety or generalization. The model remains simulator-trained and is not installed in the mod's production policy selector. The original five-feature imitation MLP stays frozen.

The next research milestone is a **read-only Minecraft shadow evaluator** with a new model artifact and stricter action masks, followed by out-of-simulator comparison across multiple real-world scenarios. No neural-driven task dispatch should be authorized solely from synthetic Q-learning success.
