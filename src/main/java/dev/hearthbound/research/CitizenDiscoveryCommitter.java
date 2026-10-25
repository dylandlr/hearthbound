package dev.hearthbound.research;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Objects;

/**
 * Transactional ingress from an already-authorized citizen operation to the
 * durable credit ledger. The Forge adapter must supply a persisted assignment
 * and an observation tied to the same durable operation ID.
 */
public final class CitizenDiscoveryCommitter {
    public record Result(boolean newlyCredited, long citizenResearchBalance,
                         CitizenDiscoveryGate.Eligible eligible) {}

    private final DurableCreditLedger ledger;

    public CitizenDiscoveryCommitter(Path existingDirectory) {
        ledger = new DurableCreditLedger(Objects.requireNonNull(existingDirectory));
    }

    /**
     * Receipt is an immutable, canonical serialization of the authoritative
     * pre-operation proof and completed Create mutation. Must be stable on retry.
     */
    public synchronized Result commit(CitizenDiscoveryGate.Assignment assignment,
                                      CitizenDiscoveryGate.Observation observation,
                                      String receipt) throws IOException {
        var eligible = CitizenDiscoveryGate.validate(assignment, observation);
        if (receipt == null || receipt.isBlank())
            throw new IllegalArgumentException("Missing authoritative receipt");
        var credit = new DurableCreditLedger.Credit(eligible.operationId(),
                eligible.citizenId(), 1, receipt);
        boolean inserted = ledger.commit(credit);
        long balance = ledger.balance(eligible.citizenId());
        return new Result(inserted, balance, eligible);
    }

    public long balance(java.util.UUID citizenId) throws IOException {
        return ledger.balance(citizenId);
    }
}
