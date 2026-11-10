package dev.hearthbound.evidence;

import java.io.IOException;
import java.util.Objects;
import java.util.UUID;

/**
 * Delivery is a separate physical side effect from extraction. A forced
 * extraction receipt NEVER proves that wheat reached the destination.
 *
 * This validator is intentionally pure Java 17. Recording an insertion
 * attempt is not inventory proof, and a successful motor return is still
 * not independently witnessed or save-atomic.
 */
public final class DeliveryBoundaryContract {
    private DeliveryBoundaryContract() {}
    public enum Decision {
        ADMIT_INSERTION_INTENT,
        DENY_NO_PICKUP,
        DENY_NOT_EXTRACTED,
        DENY_MISMATCH,
        DENY_PREVIOUS_INSERTION,
        DENY_JOURNAL_UNAVAILABLE
    }
    public record Intent(UUID world, UUID job, UUID executor,
                         String destination, long attemptedTick) {
        public Intent {
            Objects.requireNonNull(world);
            Objects.requireNonNull(job);
            Objects.requireNonNull(executor);
            if (destination == null || destination.isBlank() || destination.length() > 512
                || attemptedTick < 0)
                throw new IllegalArgumentException("invalid delivery intent");
        }
    }
    public static Decision admit(PickupTransactionJournal.View pickup,
                                 Intent delivery, boolean journalAvailable,
                                 boolean alreadyAttempted) {
        if (!journalAvailable) return Decision.DENY_JOURNAL_UNAVAILABLE;
        if (pickup == null) return Decision.DENY_NO_PICKUP;
        if (delivery == null
                || !pickup.intent().world().equals(delivery.world())
                || !pickup.intent().job().equals(delivery.job())
                || !pickup.intent().executor().equals(delivery.executor())
                || pickup.intent().attemptedTick() > delivery.attemptedTick())
            return Decision.DENY_MISMATCH;
        if (pickup.state() != PickupTransactionJournal.State.CARGO_RETURNED)
            return Decision.DENY_NOT_EXTRACTED;
        if (alreadyAttempted) return Decision.DENY_PREVIOUS_INSERTION;
        return Decision.ADMIT_INSERTION_INTENT;
    }
    public static boolean authorizesAutomaticRetry(Decision ignored) {
        return false;
    }
}
