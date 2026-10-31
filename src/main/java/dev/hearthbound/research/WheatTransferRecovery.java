package dev.hearthbound.research;

/** Conservative reconciliation after a wheat debit but before machine checkpoint. */
public final class WheatTransferRecovery {
    public enum Decision { NO_RESERVATION, CONFIRMED_INSERTED, QUARANTINE }
    public record Evidence(boolean debitRecorded, boolean matchingOperation,
                           boolean sameCitizen, boolean machineHasExpectedWheat,
                           boolean machineCheckpointDurable, boolean machineMayHaveProcessed) {}
    public static Decision assess(Evidence evidence) {
        if (evidence == null) return Decision.QUARANTINE;
        if (!evidence.debitRecorded()) {
            // Do not allow this result to authorize new inventory mutations.
            return evidence.machineHasExpectedWheat() || evidence.machineMayHaveProcessed()
                    ? Decision.QUARANTINE : Decision.NO_RESERVATION;
        }
        if (!evidence.matchingOperation() || !evidence.sameCitizen())
            return Decision.QUARANTINE;
        if (evidence.machineCheckpointDurable() && evidence.machineHasExpectedWheat()
                && !evidence.machineMayHaveProcessed())
            return Decision.CONFIRMED_INSERTED;
        // A debit without a durable checkpoint is an uncertain transfer.
        // In particular, never recreate wheat after milling may have begun.
        return Decision.QUARANTINE;
    }
    private WheatTransferRecovery() {}
}
