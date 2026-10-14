# First Mill policy contract (implementation foundation)

`ColonyPolicy` is a Java 17 dependency-free interface for the common decision layer. It is not yet wired into a Minecraft entity or Create adapter.

## Inputs
Version 1 observations carry world-version, wheat in input storage, wheat/flour being carried, output free slots, power/blockage status, operator training, and the finite set of authorized candidate actions.

## Outputs
A decision contains one whitelisted action, the expected world version, and a diagnostic reason. A validator rejects stale versions and unsupported actions. The Minecraft server action executor (not implemented yet) is responsible for rechecking at commit-time and applying inventory reservations; this contract alone does **not** guarantee item safety or atomicity.

## Initial deterministic policy
Cargo delivery takes precedence, then clearing blockages, processing carried wheat, restocking, and waiting. Missing permissions always degrade to waiting, never an unauthorized action. Missing required WAIT is treated as scheduler contract failure and must not result in state mutation.

## Experiment readiness
Future tree, forest, RL and LLM policies must satisfy the same interface and receive equivalent available-action filtering. Offline training must use separate training/held-out seeds; policy decisions must be tested in a real Minecraft server before gameplay claims.

## Standalone smoke test
With Java 17+ installed:
```sh
mkdir -p /tmp/hb-policy-classes
javac --release 17 -d /tmp/hb-policy-classes src/main/java/dev/hearthbound/policy/*.java src/test/java/dev/hearthbound/policy/*.java
java -cp /tmp/hb-policy-classes dev.hearthbound.policy.FirstMillRulesPolicySmokeTest
```
This checks decision logic only, not Create integration.
