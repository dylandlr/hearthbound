package dev.hearthbound.research;
public final class WheatTransferRecoveryTest {
    private static int passed;
    private static void check(WheatTransferRecovery.Decision expected, WheatTransferRecovery.Evidence e) {
        if (WheatTransferRecovery.assess(e) != expected) throw new AssertionError("Invalid recovery outcome: " + e);
        passed++;
    }
    public static void main(String[] args) {
        var ok = WheatTransferRecovery.Decision.CONFIRMED_INSERTED;
        var hold = WheatTransferRecovery.Decision.QUARANTINE;
        check(ok,new WheatTransferRecovery.Evidence(true,true,true,true,true,false));
        check(hold,new WheatTransferRecovery.Evidence(true,true,true,true,false,false));
        check(hold,new WheatTransferRecovery.Evidence(true,true,true,false,true,false));
        check(hold,new WheatTransferRecovery.Evidence(true,true,true,false,false,true));
        check(hold,new WheatTransferRecovery.Evidence(true,false,true,true,true,false));
        check(hold,new WheatTransferRecovery.Evidence(true,true,false,true,true,false));
        check(hold,new WheatTransferRecovery.Evidence(false,true,true,true,true,false));
        check(WheatTransferRecovery.Decision.NO_RESERVATION,
                new WheatTransferRecovery.Evidence(false,false,false,false,false,false));
        System.out.println("WheatTransferRecovery: " + passed + " checks passed");
    }
}
