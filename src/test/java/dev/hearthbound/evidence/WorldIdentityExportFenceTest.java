package dev.hearthbound.evidence;

import java.util.UUID;
import dev.hearthbound.evidence.WorldIdentityExportFence.*;

public final class WorldIdentityExportFenceTest {
    private static int checks;
    private static void check(boolean b) { checks++; if (!b) throw new AssertionError("check " + checks); }
    public static void main(String[] args) {
        UUID a = UUID.randomUUID(), b = UUID.randomUUID();
        StartupEvidence good = new StartupEvidence(a, a, true, true, true, true);
        check(WorldIdentityExportFence.evaluate(good) == Status.READY);
        WorldIdentityExportFence.requireReady(good);
        check(WorldIdentityExportFence.evaluate(new StartupEvidence(null,a,true,true,true,true)) == Status.UNINITIALIZED);
        check(WorldIdentityExportFence.evaluate(new StartupEvidence(a,a,true,false,true,true)) == Status.UNINITIALIZED);
        check(WorldIdentityExportFence.evaluate(new StartupEvidence(a,null,true,true,true,true)) == Status.FILE_NOT_VERIFIED);
        check(WorldIdentityExportFence.evaluate(new StartupEvidence(a,a,false,true,true,true)) == Status.FILE_NOT_VERIFIED);
        check(WorldIdentityExportFence.evaluate(new StartupEvidence(a,b,true,true,true,true)) == Status.ID_MISMATCH);
        check(WorldIdentityExportFence.evaluate(new StartupEvidence(a,a,true,true,false,true)) == Status.JOURNAL_MISMATCH);
        check(WorldIdentityExportFence.evaluate(new StartupEvidence(a,a,true,true,true,false)) == Status.ROLLBACK_UNVERIFIED);
        boolean rejected=false;
        try { WorldIdentityExportFence.requireReady(new StartupEvidence(a,b,true,true,true,true)); }
        catch (IllegalStateException ex) { rejected=true; }
        check(rejected);
        System.out.println("PASS " + checks + " checks");
    }
}
