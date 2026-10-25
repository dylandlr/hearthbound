package dev.hearthbound.research;

import java.io.IOException;
import java.nio.file.Path;
import java.util.Objects;
import java.util.UUID;

/**
 * Durable debit journal for citizen wheat reservations.
 * Uses the existing append-only operation ledger: each transfer can debit once.
 * This is not yet an atomic cross-inventory Minecraft transaction.
 */
public final class DurableCitizenInventory {
    private final DurableCreditLedger debits;
    private final int initialWheat;
    private final UUID citizen;

    public DurableCitizenInventory(Path existingDirectory, UUID citizen, int initialWheat) {
        if (initialWheat < 0) throw new IllegalArgumentException("Negative starting inventory");
        this.citizen = Objects.requireNonNull(citizen);
        this.initialWheat = initialWheat;
        this.debits = new DurableCreditLedger(existingDirectory);
    }

    public synchronized int available() throws IOException {
        long used = debits.balance(citizen);
        if (used > initialWheat) throw new IOException("Inventory overspent");
        return Math.toIntExact(initialWheat - used);
    }

    /**
     * Debit is persisted before the machine is allowed to accept wheat.
     * Reconciliation is required if process crashes between the debit and
     * Create input insertion; do not blindly repeat the machine mutation.
     */
    public synchronized boolean reserve(UUID operationId) throws IOException {
        Objects.requireNonNull(operationId);
        if (available() < 1) {
            // A previously successful reservation can be queried via a stable
            // receipt by the caller, but no new reservation can overdraw stock.
            throw new IOException("No unreserved wheat");
        }
        return debits.commit(new DurableCreditLedger.Credit(operationId, citizen, 1,
                "hearthbound:citizen_wheat_debit:v1:" + citizen + ":" + operationId));
    }
}
