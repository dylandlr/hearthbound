#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
javac --release 17 -d "$OUT" \
  src/main/java/dev/hearthbound/policy/*.java \
  src/main/java/dev/hearthbound/agent/v02/*.java \
  src/main/java/dev/hearthbound/jobs/StationReservations.java \
  src/main/java/dev/hearthbound/jobs/TravelProgress.java \
  src/main/java/dev/hearthbound/jobs/TransferLedger.java \
  src/test/java/dev/hearthbound/policy/*.java \
  src/test/java/dev/hearthbound/agent/v02/*.java \
  src/test/java/dev/hearthbound/jobs/StationReservationsSmokeTest.java \
  src/test/java/dev/hearthbound/jobs/TravelProgressSmokeTest.java \
  src/test/java/dev/hearthbound/jobs/TransferLedgerSmokeTest.java \
  src/test/java/dev/hearthbound/jobs/TransferLedgerPropertySmokeTest.java
java -cp "$OUT" dev.hearthbound.policy.FirstMillRulesPolicySmokeTest
java -cp "$OUT" dev.hearthbound.agent.v02.AgentArchitectureV02SmokeTest
java -cp "$OUT" dev.hearthbound.agent.v02.TrajectoryDatasetV02SmokeTest
java -cp "$OUT" dev.hearthbound.policy.FirstMillPolicyBoundarySmokeTest
java -cp "$OUT" dev.hearthbound.jobs.StationReservationsSmokeTest
java -cp "$OUT" dev.hearthbound.jobs.TravelProgressSmokeTest
java -cp "$OUT" dev.hearthbound.jobs.TransferLedgerSmokeTest
java -cp "$OUT" dev.hearthbound.jobs.TransferLedgerPropertySmokeTest
echo 'PASS: all standalone Java core tests'
