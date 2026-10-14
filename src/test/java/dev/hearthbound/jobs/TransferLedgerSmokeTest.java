package dev.hearthbound.jobs;
public final class TransferLedgerSmokeTest {
    static void check(boolean ok, String msg) { if (!ok) throw new AssertionError(msg); }
    public static void main(String[] args) {
        TransferLedger t = new TransferLedger("job-1", "minecraft:wheat", 4);
        check(t.phase() == TransferLedger.Phase.PLANNED, "initial");
        check(!t.deliver(), "cannot deliver before withdrawing");
        check(t.withdraw(), "first withdrawal");
        check(!t.withdraw(), "duplicate withdrawal");
        check(!t.cancel(), "cannot cancel cargo in flight");
        check(t.deliver(), "delivered");
        check(!t.deliver(), "duplicate delivery");
        check(!t.withdraw(), "cannot restart completed transfer");
        TransferLedger restart = TransferLedger.restore(t.id(), t.itemId(), t.quantity(), TransferLedger.Phase.WITHDRAWN);
        check(restart.deliver(), "reconcile then deliver");
        TransferLedger abort = new TransferLedger("job-2", "minecraft:wheat", 3);
        check(abort.cancel() && !abort.withdraw(), "cancel planned");
        boolean rejected = false;
        try { new TransferLedger("", "minecraft:wheat", 1); } catch (IllegalArgumentException e) { rejected = true; }
        check(rejected, "empty id rejected");
        System.out.println("PASS: transfer state transitions and replay guards");
    }
}
