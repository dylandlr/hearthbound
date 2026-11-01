package dev.hearthbound.evidence;

import java.nio.file.*;
import java.util.UUID;
import dev.hearthbound.evidence.VerifiedMillAttribution.*;
import dev.hearthbound.evidence.WorldIdentityExportFence.StartupEvidence;

public final class ResearchExportAdmissionTest {
    static int checks;
    static void check(boolean ok) { checks++; if (!ok) throw new AssertionError("check " + checks); }
    static boolean denied(Path p, UUID w, StartupEvidence e, Proof proof) {
        try { ResearchExportAdmission.authorize(p,w,e,proof); return false; }
        catch (IllegalStateException | IllegalArgumentException ex) { return true; }
        catch (java.io.IOException ex) { throw new RuntimeException(ex); }
    }
    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("hb-admission");
        Path marker = dir.resolve("world.id");
        try {
            UUID w = UUID.randomUUID(), foreign = UUID.randomUUID();
            UUID job=UUID.randomUUID(), citizen=UUID.randomUUID();
            StartupEvidence verified = new StartupEvidence(w,w,true,true,true,true);
            Proof good = new Proof(w,job,citizen,"minecraft:overworld",123,10,20,1,0,0,1,true,false);
            check(denied(marker,w,verified,good)); // no marker: never auto-create with journals
            check(WorldStartupCheckpoint.verify(marker,w,false,false)
                == WorldStartupCheckpoint.Status.RESTART_REQUIRED);
            check(ResearchExportAdmission.authorize(marker,w,verified,good).citizenId().equals(citizen.toString()));
            check(denied(marker,w,new StartupEvidence(w,w,true,true,false,true),good));
            check(denied(marker,w,new StartupEvidence(w,w,true,true,true,false),good));
            check(denied(marker,w,new StartupEvidence(w,w,false,true,true,true),good));
            check(denied(marker,w,verified,new Proof(foreign,job,citizen,"minecraft:overworld",123,10,20,1,0,0,1,true,false)));
            check(denied(marker,w,verified,new Proof(w,job,citizen,"minecraft:overworld",123,10,20,1,0,0,1,true,true)));
            check(denied(marker,foreign,verified,good));
            Files.writeString(marker,"corrupted\n");
            check(denied(marker,w,verified,good));
            System.out.println("PASS " + checks + " checks");
        } finally {
            try(var stream=Files.walk(dir)) {
                stream.sorted(java.util.Comparator.reverseOrder()).forEach(p->{
                    try { Files.deleteIfExists(p); } catch(java.io.IOException e) { throw new RuntimeException(e); }
                });
            }
        }
    }
}
