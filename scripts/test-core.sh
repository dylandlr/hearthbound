#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
javac --release 17 -d "$OUT" \
  src/main/java/dev/hearthbound/policy/*.java \
  src/main/java/dev/hearthbound/jobs/TravelProgress.java \
  src/main/java/dev/hearthbound/jobs/TransferLedger.java \
  src/test/java/dev/hearthbound/policy/*.java \
  src/test/java/dev/hearthbound/jobs/TravelProgressSmokeTest.java \
  src/test/java/dev/hearthbound/jobs/TransferLedgerSmokeTest.java \
  src/test/java/dev/hearthbound/jobs/TransferLedgerPropertySmokeTest.java
java -cp "$OUT" dev.hearthbound.policy.FirstMillRulesPolicySmokeTest
java -cp "$OUT" dev.hearthbound.jobs.TravelProgressSmokeTest
java -cp "$OUT" dev.hearthbound.jobs.TransferLedgerSmokeTest
java -cp "$OUT" dev.hearthbound.jobs.TransferLedgerPropertySmokeTest
echo 'PASS: all standalone Java core tests'
