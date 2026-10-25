package dev.hearthbound.integration;

/**
 * Pure decision contract for recovery of an unresolved citizen wheat delivery.
 * No evidence state can authorize a blind replay of a Create inventory mutation.
 */
public final class CitizenSupplyRecovery {
    private CitizenSupplyRecovery() {}
    public enum Decision { NOT_STARTED, COMPLETED_OBSERVED, AMBIGUOUS_BLOCKED }
    public record Evidence(boolean durableAttempt, boolean machineContainsWheat,
                           int citizenWheat, int expectedBefore,
                           boolean sameOperationReceipt, boolean taskIdle) {}
    public static Decision classify(Evidence evidence) {
        if(evidence==null || evidence.expectedBefore()<1 || evidence.citizenWheat()<0)
            return Decision.AMBIGUOUS_BLOCKED;
        if(!evidence.durableAttempt())
            return Decision.NOT_STARTED;
        if(evidence.sameOperationReceipt() && evidence.taskIdle()
                && evidence.citizenWheat()==evidence.expectedBefore()-1)
            return Decision.COMPLETED_OBSERVED;
        return Decision.AMBIGUOUS_BLOCKED;
    }
}
