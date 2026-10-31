package dev.hearthbound.evidence;

import java.util.UUID;
import dev.hearthbound.evidence.VerifiedMillAttribution.*;

/** Standalone Java 17 contract checks; not a Forge client/server integration test. */
public final class VerifiedMillAttributionTest {
    private static int checks;
    private static void ok(boolean b) { checks++; if (!b) throw new AssertionError(); }
    private static void rejected(Proof p) {
        boolean failed = false;
        try { VerifiedMillAttribution.validate(p); }
        catch (IllegalArgumentException e) { failed = true; }
        ok(failed);
    }
    public static void main(String[] args) {
        UUID w = UUID.randomUUID(), j = UUID.randomUUID(), c = UUID.randomUUID();
        Proof p = new Proof(w,j,c,"minecraft:overworld",42,100,120,1,0,0,1,true,false);
        Claim a = VerifiedMillAttribution.validate(p);
        ok(a.equals(VerifiedMillAttribution.validate(p)));
        ok(a.citizenId().equals(c.toString()));
        ok(a.eventId().contains(w.toString()));
        rejected(new Proof(w,j,c,"minecraft:overworld",42,100,120,1,0,0,1,false,false));
        rejected(new Proof(w,j,c,"minecraft:overworld",42,100,120,1,0,0,1,true,true));
        rejected(new Proof(w,j,c,"minecraft:overworld",42,-1,120,1,0,0,1,true,false));
        rejected(new Proof(w,j,c,"minecraft:overworld",42,120,120,1,0,0,1,true,false));
        rejected(new Proof(w,j,c,"minecraft:overworld",42,100,120,1,1,0,1,true,false));
        rejected(new Proof(w,j,c,"minecraft:overworld",42,100,120,1,0,0,0,true,false));
        rejected(new Proof(w,j,c,"minecraft:overworld",42,100,120,2,0,0,1,true,false));
        System.out.println("PASS " + checks + " checks");
    }
}
