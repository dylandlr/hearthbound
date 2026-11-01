package dev.hearthbound.evidence;

import java.nio.file.*;
import java.util.UUID;
import dev.hearthbound.evidence.WorldStartupCheckpoint.Status;

public final class WorldStartupCheckpointTest {
    static int checks;
    static void ok(boolean value) { checks++; if (!value) throw new AssertionError("check " + checks); }
    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("hb-checkpoint-test");
        try {
            UUID a = UUID.randomUUID(), b = UUID.randomUUID();
            Path marker = dir.resolve("world.identity");
            ok(WorldStartupCheckpoint.verify(marker, a, true, true) == Status.MISSING_WITH_JOURNAL);
            ok(!Files.exists(marker));
            ok(WorldStartupCheckpoint.verify(marker, a, false, false) == Status.RESTART_REQUIRED);
            ok(Files.exists(marker));
            ok(Files.readString(marker).equals(a + "\n"));
            ok(WorldStartupCheckpoint.verify(marker, a, false, true) == Status.READY);
            ok(WorldStartupCheckpoint.verify(marker, a, true, true) == Status.READY);
            ok(WorldStartupCheckpoint.verify(marker, a, true, false) == Status.ROLLBACK_UNVERIFIED);
            ok(WorldStartupCheckpoint.verify(marker, b, true, true) == Status.ID_MISMATCH);
            Files.writeString(marker, "garbage\n");
            ok(WorldStartupCheckpoint.verify(marker, a, true, true) == Status.ID_MISMATCH);
            boolean failed = false;
            try { WorldStartupCheckpoint.verify(marker, null, true, true); }
            catch (IllegalArgumentException e) { failed = true; }
            ok(failed);
            Files.writeString(marker, "x".repeat(80));
            failed = false;
            try { WorldStartupCheckpoint.verify(marker, a, true, true); }
            catch (java.io.IOException e) { failed = true; }
            ok(failed);
            System.out.println("PASS " + checks + " checks");
        } finally {
            try (var walk = Files.walk(dir)) {
                walk.sorted(java.util.Comparator.reverseOrder()).forEach(p -> {
                    try { Files.deleteIfExists(p); } catch (Exception ignored) {}
                });
            }
        }
    }
}
