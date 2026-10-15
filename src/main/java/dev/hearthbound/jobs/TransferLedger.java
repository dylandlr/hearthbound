package dev.hearthbound.jobs;

/** Single-server-thread, crash-replay-friendly abstract transfer state.
 * No physical items are mutated here: the Minecraft adapter must reconcile and commit.
 */
public final class TransferLedger {
    public enum Phase { PLANNED, WITHDRAWN, DELIVERED, CANCELLED }
    private final String id;
    private final String itemId;
    private final int quantity;
    private Phase phase = Phase.PLANNED;
    public TransferLedger(String id, String itemId, int quantity) {
        if (id == null || id.isBlank() || itemId == null || itemId.isBlank() || quantity <= 0)
            throw new IllegalArgumentException("Invalid transfer");
        this.id = id;
        this.itemId = itemId;
        this.quantity = quantity;
    }
    public String id() { return id; }
    public String itemId() { return itemId; }
    public int quantity() { return quantity; }
    public Phase phase() { return phase; }
    public boolean withdraw() {
        if (phase != Phase.PLANNED) return false;
        phase = Phase.WITHDRAWN;
        return true;
    }
    public boolean deliver() {
        if (phase != Phase.WITHDRAWN) return false;
        phase = Phase.DELIVERED;
        return true;
    }
    public boolean cancel() {
        if (phase != Phase.PLANNED) return false;
        phase = Phase.CANCELLED;
        return true;
    }
    /** Restores a phase only after the Minecraft adapter reconciles physical inventory. */
    public static TransferLedger restore(String id, String itemId, int quantity, Phase phase) {
        if (phase == null) throw new IllegalArgumentException("Missing phase");
        TransferLedger ledger = new TransferLedger(id, itemId, quantity);
        ledger.phase = phase;
        return ledger;
    }
}
