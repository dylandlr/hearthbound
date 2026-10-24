package dev.hearthbound.research;

import java.util.Objects;
import dev.hearthbound.research.MillstoneReceiptGate.*;

/**
 * Recovery policy for durable operation evidence, not diagnostic observations.
 * READY requires an atomic insert-if-absent credit transaction by the caller.
 * This class neither grants rewards nor proves that its inputs reached disk.
 */
public final class MillstoneRecoveryGate {
    public enum CreditState { ABSENT, MATCHING, CONFLICTING, UNKNOWN }
    public enum Decision { QUARANTINE, ALREADY_CREDITED, READY_FOR_ATOMIC_CREDIT }
    public record Result(Decision decision, String reason, Accepted receipt) {}

    public static Result recover(InputProof proof, Completion completion, CreditState credit) {
        Objects.requireNonNull(credit);
        if (proof == null || completion == null)
            return quarantine("incomplete_operation");
        Accepted accepted;
        try {
            accepted = MillstoneReceiptGate.validate(proof, completion);
        } catch (IllegalArgumentException invalid) {
            return quarantine("conflicting_operation");
        }
        // CreditState must come from a durable lookup by operation ID, comparing
        // the entire accepted receipt. A failed lookup is UNKNOWN, never ABSENT.
        return switch (credit) {
            case UNKNOWN -> quarantine("credit_lookup_unknown");
            case CONFLICTING -> quarantine("conflicting_credit");
            case MATCHING -> new Result(Decision.ALREADY_CREDITED, "duplicate_operation", null);
            case ABSENT -> new Result(Decision.READY_FOR_ATOMIC_CREDIT, "complete_operation", accepted);
        };
    }

    private static Result quarantine(String reason) {
        return new Result(Decision.QUARANTINE, reason, null);
    }
    private MillstoneRecoveryGate() {}
}
