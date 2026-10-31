package dev.hearthbound.research;

import java.util.Objects;
import java.util.UUID;

/**
 * Fail-closed authorization for retiring a machine claim. A claim file must
 * remain protected until a separate atomic retirement mechanism is added.
 */
public final class MachineClaimRetirementGate {
    public enum Decision { KEEP_CLAIM, ELIGIBLE_FOR_RETIREMENT }
    public record Evidence(UUID operationId, UUID citizenId,
                           boolean operationReceiptDurable,
                           boolean citizenCreditDurable,
                           boolean machineCheckpointDurable,
                           boolean machineIdle,
                           boolean transferReconciled,
                           boolean evidenceConflict) {}
    public static Decision evaluate(DurableMachineClaim.Claim claim, Evidence proof) {
        if (claim == null || proof == null) return Decision.KEEP_CLAIM;
        if (!Objects.equals(claim.operationId(), proof.operationId())
                || !Objects.equals(claim.citizenId(), proof.citizenId())
                || !proof.operationReceiptDurable()
                || !proof.citizenCreditDurable()
                || !proof.machineCheckpointDurable()
                || !proof.machineIdle()
                || !proof.transferReconciled()
                || proof.evidenceConflict())
            return Decision.KEEP_CLAIM;
        return Decision.ELIGIBLE_FOR_RETIREMENT;
    }
    private MachineClaimRetirementGate() {}
}
