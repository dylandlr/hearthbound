#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/survival-test
# Some minimal JDK images contain jdk.compiler but omit the javac executable.
java -m jdk.compiler/com.sun.tools.javac.Main --release 17 -d build/survival-test \
  src/main/java/dev/hearthbound/research/CitizenTaskArbiter.java \
  src/main/java/dev/hearthbound/ai/*.java src/test/java/dev/hearthbound/ai/*.java
for suite in SurvivalPolicyTest PolicyKernelTest HaulLedgerTest WorkOfferLifecycleTest; do
  java -cp build/survival-test "dev.hearthbound.ai.$suite"
done
