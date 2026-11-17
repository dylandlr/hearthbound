package dev.hearthbound.evidence;

import java.util.List;
import java.util.Objects;

/**
 * Strict source quarantine for report-policy pickups. Different job UUIDs
 * cannot authorize extracting again at a source whose prior cargo fate is
 * unknown. EXTRACTION_EMPTY is not a positive inventory proof and does not
 * authorize reward; it simply does not create a cargo-duplication hazard.
 *
 * CARGO_RETURNED is an extraction receipt, NOT a delivery receipt. Until
 * separately reconciled it blocks reusing this source, even if a villager
 * appears to have finished its old job. This conservative policy may block
 * useful repeat hauls; resolving that needs a separate durable delivery
 * protocol and independent physical inventory evidence.
 */
public final class PickupSourceAdmission {
    private PickupSourceAdmission() {}

    public enum Decision {
        ALLOW_NO_CONFLICT,
        DENY_UNRESOLVED_EXTRACTION,
        DENY_UNRECONCILED_CARGO,
        DENY_REUSED_JOB_ID,
        DENY_INVALID_REQUEST
    }

    public static Decision classify(List<PickupTransactionJournal.View> prior,
                                    PickupTransactionJournal.Intent proposed) {
        if (prior == null || proposed == null
                || proposed.source() == null || proposed.source().isBlank())
            return Decision.DENY_INVALID_REQUEST;
        Decision decision = Decision.ALLOW_NO_CONFLICT;
        for (PickupTransactionJournal.View entry : prior) {
            if (entry == null || entry.intent() == null)
                return Decision.DENY_INVALID_REQUEST;
            PickupTransactionJournal.Intent old = entry.intent();
            if (!Objects.equals(old.world(), proposed.world()))
                return Decision.DENY_INVALID_REQUEST;
            if (old.job().equals(proposed.job()))
                return Decision.DENY_REUSED_JOB_ID;
            if (!old.source().equals(proposed.source()))
                continue;
            if (entry.state() == PickupTransactionJournal.State.UNRESOLVED)
                return Decision.DENY_UNRESOLVED_EXTRACTION;
            if (entry.state() == PickupTransactionJournal.State.CARGO_RETURNED)
                decision = Decision.DENY_UNRECONCILED_CARGO;
        }
        return decision;
    }
}
