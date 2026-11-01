package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.util.UUID;

/** Fail-closed journal ownership marker; single writer and trusted world UUID required. */
public final class JournalWorldBinding {
    public enum Result { RESTART_REQUIRED, VERIFIED }
    private JournalWorldBinding() {}

    public static Result verify(Path folder, UUID world, Path inbox, Path rewards) throws IOException {
        if (world == null) throw new IllegalArgumentException("Missing world ID");
        Path base = folder.toAbsolutePath().normalize();
        Path marker = base.resolve("hearthbound-journals.world");
        if (Files.isSymbolicLink(base) || Files.isSymbolicLink(marker))
            throw new IOException("Symlink not allowed");
        if (!inbox.toAbsolutePath().normalize().getParent().equals(base)
                || !rewards.toAbsolutePath().normalize().getParent().equals(base))
            throw new IOException("Journals must reside in binding folder");
        if (Files.exists(marker)) {
            if (!Files.isRegularFile(marker) || Files.size(marker) > 128)
                throw new IOException("Invalid journal owner marker");
            String expected = "hearthbound-journals-v1\n" + world + "\n";
            if (!expected.equals(Files.readString(marker)))
                throw new IOException("Journal world mismatch or damaged marker");
            return Result.VERIFIED;
        }
        if (Files.exists(inbox) || Files.exists(rewards))
            throw new IOException("Unbound existing journals; migration required");
        Files.createDirectories(base);
        byte[] bytes = ("hearthbound-journals-v1\n" + world + "\n")
            .getBytes(java.nio.charset.StandardCharsets.US_ASCII);
        try (FileChannel file = FileChannel.open(marker, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) file.write(buffer);
            file.force(true);
        }
        try (FileChannel directory = FileChannel.open(base, StandardOpenOption.READ)) {
            directory.force(true);
        }
        return Result.RESTART_REQUIRED;
    }
}
