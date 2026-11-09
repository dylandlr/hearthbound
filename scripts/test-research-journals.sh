#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
OUT="${TMPDIR:-/tmp}/hearthbound-research-verify-$$"
trap 'rm -rf "$OUT"' EXIT
mkdir -p "$OUT"
BASE=src/main/java/dev/hearthbound/evidence
TEST=src/test/java/dev/hearthbound/evidence
javac --release 17 -d "$OUT" \
  "$BASE/WorldIdentityCodec.java" \
  "$BASE/WorldIdentityExportFence.java" \
  "$BASE/WorldStartupCheckpoint.java" \
  "$BASE/VerifiedMillAttribution.java" \
  "$BASE/ResearchExportAdmission.java" \
  "$BASE/AttributedMillInbox.java" \
  "$BASE/DurableRewardLedger.java" \
  "$BASE/ResearchReceiptDelivery.java" \
  "$BASE/ResearchJournalRuntime.java" \
  "$BASE/OutcomeLedger.java" \
  "$BASE/CausalEvidenceJournal.java" \
  "$BASE/DirectSourceWitnessContract.java" \
  "$BASE/ReportConditionedChoice.java" \
  "$BASE/ReportChoiceMlp.java" \
  "$BASE/PickupFailureContract.java" \
  "$BASE/PickupTransactionJournal.java" \
  "$BASE/PickupRecoveryGate.java" \
  "$BASE/PickupJournalOwnership.java" \
  "$BASE/PickupCitizenReconciliation.java" \
  "$BASE/ReportSessionFence.java" \
  "$BASE/JournalWorldBinding.java" \
  "$TEST/WorldIdentityCodecTest.java" \
  "$TEST/WorldIdentityExportFenceTest.java" \
  "$TEST/WorldStartupCheckpointTest.java" \
  "$TEST/VerifiedMillAttributionTest.java" \
  "$TEST/ResearchExportAdmissionTest.java" \
  "$TEST/ResearchJournalRuntimeTest.java" \
  "$TEST/JournalWorldBindingTest.java" \
  "$TEST/OutcomeLedgerTest.java" \
  "$TEST/CausalEvidenceJournalTest.java" \
  "$TEST/CausalEvidenceJournalFaultTest.java" \
  "$TEST/DirectSourceWitnessContractTest.java" \
  "$TEST/ReportConditionedChoiceTest.java" \
  "$TEST/ReportChoiceMlpTest.java" \
  "$TEST/PickupFailureContractTest.java" \
  "$TEST/PickupTransactionJournalTest.java" \
  "$TEST/PickupRecoveryGateTest.java" \
  "$TEST/PickupJournalOwnershipTest.java" \
  "$TEST/PickupCitizenReconciliationTest.java" \
  "$TEST/PickupJournalForcedKillTest.java" \
  "$TEST/ReportSessionFenceTest.java"
for cls in \
  WorldIdentityCodecTest \
  WorldIdentityExportFenceTest \
  WorldStartupCheckpointTest \
  VerifiedMillAttributionTest \
  ResearchExportAdmissionTest \
  JournalWorldBindingTest \
  ResearchJournalRuntimeTest \
  OutcomeLedgerTest \
  CausalEvidenceJournalTest \
  CausalEvidenceJournalFaultTest \
  DirectSourceWitnessContractTest \
  ReportConditionedChoiceTest \
  ReportChoiceMlpTest \
  PickupFailureContractTest \
  PickupTransactionJournalTest \
  PickupRecoveryGateTest \
  PickupJournalOwnershipTest \
  PickupCitizenReconciliationTest \
  PickupJournalForcedKillTest \
  ReportSessionFenceTest; do
  echo "== $cls =="
  java -ea -cp "$OUT" "dev.hearthbound.evidence.$cls"
done
echo "All standalone research journal suites passed"
