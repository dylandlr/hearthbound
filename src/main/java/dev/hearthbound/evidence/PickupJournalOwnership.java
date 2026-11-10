package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.LinkOption;
import java.nio.file.StandardOpenOption;
import java.nio.charset.StandardCharsets;
import java.util.Objects;
import java.util.UUID;

/**
 * Binds a pickup journal to one world and prevents silent regeneration after
 * a crash, a missing file, or a mixed backup. No automatic migration or repair.
 *
 * A new installation reserves the marker first, creates/forces the journal,
 * then forces the marker and directory. A crash between these operations
 * intentionally leaves a mismatched or invalid pair that fails closed.
 */
public final class PickupJournalOwnership {
    public static final String JOURNAL = "pickup-extraction-v1.bin";
    public static final String MARKER = "pickup-extraction-v1.world";
    private static final String PREFIX = "hearthbound-pickup-journal-v1\n";
    private PickupJournalOwnership() {}

    public static PickupTransactionJournal open(Path folder, UUID world) throws IOException {
        Objects.requireNonNull(world, "world");
        Path directory = Objects.requireNonNull(folder, "folder").toAbsolutePath().normalize();
        Path marker = directory.resolve(MARKER);
        Path journal = directory.resolve(JOURNAL);
        if (Files.isSymbolicLink(directory) || Files.isSymbolicLink(marker)
                || Files.isSymbolicLink(journal))
            throw new IOException("pickup journal symlink not allowed");
        boolean hasMarker = Files.exists(marker, LinkOption.NOFOLLOW_LINKS);
        boolean hasJournal = Files.exists(journal, LinkOption.NOFOLLOW_LINKS);
        if (hasMarker != hasJournal)
            throw new IOException("pickup journal/owner mismatch; manual review required");
        if (hasMarker) {
            if (!Files.isRegularFile(marker, LinkOption.NOFOLLOW_LINKS)
                    || !Files.isRegularFile(journal, LinkOption.NOFOLLOW_LINKS)
                    || Files.size(marker) > 128 || Files.size(journal) < 24)
                throw new IOException("invalid existing pickup evidence files");
            String expected = PREFIX + world + "\n";
            if (!expected.equals(Files.readString(marker, StandardCharsets.US_ASCII)))
                throw new IOException("pickup journal owner/world mismatch");
            // Its header, frames and world UUID are independently verified here.
            return new PickupTransactionJournal(journal, world);
        }

        Files.createDirectories(directory);
        if (Files.isSymbolicLink(directory))
            throw new IOException("pickup journal directory replaced by symlink");
        // New installation. CREATE_NEW reservation prevents another marker
        // from being silently accepted if it appeared between checks.
        try (FileChannel markerReservation = FileChannel.open(marker,
                StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            // The marker is reserved first. A crash here leaves an invalid
            // marker-without-journal pair and thus fails closed on reboot.
            try (PickupTransactionJournal opened = new PickupTransactionJournal(journal, world)) {
                byte[] bytes = (PREFIX + world + "\n").getBytes(StandardCharsets.US_ASCII);
                ByteBuffer buffer = ByteBuffer.wrap(bytes);
                while (buffer.hasRemaining()) markerReservation.write(buffer);
                markerReservation.force(true);
            }
        }
        try (FileChannel directoryChannel = FileChannel.open(directory, StandardOpenOption.READ)) {
            directoryChannel.force(true);
        }
        return new PickupTransactionJournal(journal, world);
    }
}
