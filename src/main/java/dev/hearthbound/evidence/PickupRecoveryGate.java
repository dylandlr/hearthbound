package dev.hearthbound.evidence;

import java.util.UUID;

/**
 * Fail-closed restart classification. These are restrictions, never permission
 * to retry, transfer cargo or mint a negative experience. Caller must also
 * prove the saved villager identity/world/job and current inventory independently.
 */
public final class PickupRecoveryGate {
    private PickupRecoveryGate() {}
    public enum Decision {
        PAUSE_NO_INTENT,
        QUARANTINE_UNRESOLVED,
        PAUSE_EMPTY_OUTCOME,
        QUARANTINE_CARGO_OUTCOME,
        QUARANTINE_IDENTITY_MISMATCH,
        QUARANTINE_JOURNAL_UNAVAILABLE
    }
    public static Decision classify(UUID world, UUID executor, UUID job,
                                    PickupTransactionJournal.View recorded,
                                    boolean journalAvailable) {
        if (!journalAvailable) return Decision.QUARANTINE_JOURNAL_UNAVAILABLE;
        if (world == null || executor == null || job == null)
            return Decision.QUARANTINE_IDENTITY_MISMATCH;
        if (recorded == null) return Decision.PAUSE_NO_INTENT;
        PickupTransactionJournal.Intent intent = recorded.intent();
        if (!world.equals(intent.world()) || !executor.equals(intent.executor())
                || !job.equals(intent.job()))
            return Decision.QUARANTINE_IDENTITY_MISMATCH;
        return switch (recorded.state()) {
            case UNRESOLVED -> Decision.QUARANTINE_UNRESOLVED;
            case EXTRACTION_EMPTY -> Decision.PAUSE_EMPTY_OUTCOME;
            case CARGO_RETURNED -> Decision.QUARANTINE_CARGO_OUTCOME;
        };
    }
}
