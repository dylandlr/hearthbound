package dev.hearthbound.evidence;

import java.util.UUID;

public final class WorldIdentityCodecTest {
    private static int n;
    private static void check(boolean b) { n++; if (!b) throw new AssertionError("check " + n); }
    private static void reject(String s) {
        boolean bad=false;
        try { WorldIdentityCodec.decode(s); } catch (IllegalArgumentException ex) { bad=true; }
        check(bad);
    }
    public static void main(String[] args) {
        UUID id=WorldIdentityCodec.create();
        String persisted=WorldIdentityCodec.encode(id);
        check(id.equals(WorldIdentityCodec.decode(persisted)));
        check(persisted.equals(WorldIdentityCodec.encode(WorldIdentityCodec.decode(persisted))));
        check(!id.equals(WorldIdentityCodec.create()));
        reject(null);
        reject("");
        reject("not-a-uuid");
        reject(persisted.toUpperCase());
        reject("0".repeat(36));
        reject(" " + persisted);
        System.out.println("PASS " + n + " checks");
    }
}
