package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.util.UUID;

/** Independent durable identity marker. Does not itself verify Minecraft SavedData durability. */
public final class WorldStartupCheckpoint {
    public enum Status { RESTART_REQUIRED, READY, MISSING_WITH_JOURNAL, ID_MISMATCH, ROLLBACK_UNVERIFIED }
    private WorldStartupCheckpoint() {}

    public static Status verify(Path marker, UUID savedDataWorldId, boolean journalExists,
                                boolean rollbackReconciled) throws IOException {
        if (savedDataWorldId == null) throw new IllegalArgumentException("No saved world ID");
        if (Files.isSymbolicLink(marker)) throw new IOException("Identity marker symlink refused");
        if (!Files.exists(marker)) {
            if (journalExists) return Status.MISSING_WITH_JOURNAL;
            Path parent = marker.toAbsolutePath().getParent();
            Files.createDirectories(parent);
            Path tmp = Files.createTempFile(parent, "world-identity-", ".tmp");
            boolean moved = false;
            try {
                byte[] bytes = (savedDataWorldId.toString() + "\n").getBytes(java.nio.charset.StandardCharsets.US_ASCII);
                try (FileChannel ch = FileChannel.open(tmp, StandardOpenOption.WRITE)) {
                    ch.write(ByteBuffer.wrap(bytes));
                    ch.force(true);
                }
                Files.move(tmp, marker, StandardCopyOption.ATOMIC_MOVE);
                moved = true;
                try (FileChannel dir = FileChannel.open(parent, StandardOpenOption.READ)) { dir.force(true); }
                catch (UnsupportedOperationException ex) { throw new IOException("Directory fsync unsupported", ex); }
            } finally { if (!moved) Files.deleteIfExists(tmp); }
            return Status.RESTART_REQUIRED;
        }
        if (!Files.isRegularFile(marker) || Files.size(marker) > 64) throw new IOException("Invalid identity marker");
        String stored = Files.readString(marker, java.nio.charset.StandardCharsets.US_ASCII);
        if (!stored.equals(savedDataWorldId.toString() + "\n")) return Status.ID_MISMATCH;
        if (!rollbackReconciled) return Status.ROLLBACK_UNVERIFIED;
        return Status.READY;
    }
}
