package dev.hearthbound.ai;

import static dev.hearthbound.ai.HaulLedger.State.*;

public final class HaulLedgerTest {
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
    private static void rejects(Runnable block, String message) {
        try { block.run(); throw new AssertionError(message); }
        catch (IllegalStateException expected) { /* expected */ }
    }
    public static void main(String[] args) {
        HaulLedger ledger = new HaulLedger();
        var first = ledger.reserve("sable", "chest-A", "chest-B", 1);
        check(ledger.outstanding() == 1, "one outstanding reservation");
        rejects(() -> ledger.reserve("iven", "chest-A", "chest-C", 1), "double reservation");
        ledger.transition(first.id(), RESERVED, IN_TRANSIT);
        rejects(() -> ledger.transition(first.id(), RESERVED, IN_TRANSIT), "stale transition");
        rejects(() -> ledger.transition(first.id(), IN_TRANSIT, CANCELLED), "invalid rollback");
        ledger.transition(first.id(), IN_TRANSIT, COMPLETE);
        check(ledger.outstanding() == 0, "completed released");
        rejects(() -> ledger.transition(first.id(), IN_TRANSIT, COMPLETE), "duplicate delivery");
        var second = ledger.reserve("iven", "chest-A", "chest-C", 1);
        ledger.transition(second.id(), RESERVED, CANCELLED);
        check(ledger.outstanding() == 0, "cancelled released");
        check(ledger.get(first.id()).state() == COMPLETE, "completed ticket retained");
        System.out.println("HaulLedgerTest: 8 checks passed");
    }
}
