package dev.hearthbound.world;

import dev.hearthbound.evidence.PickupTransactionJournal;
import java.io.IOException;
import java.nio.file.Path;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.storage.LevelResource;

/**
 * Server-thread-only bridge to the fsynced physical extraction journal.
 * Only report-policy hauling uses this experimental path. Failures do not
 * allow extraction to proceed, and no replay authorizes inventory actions.
 */
final class PickupJournalBridge {
    private static final Map<MinecraftServer, PickupTransactionJournal> OPEN = new WeakHashMap<>();
    private static final Map<MinecraftServer, String> BLOCKED = new WeakHashMap<>();
    private PickupJournalBridge() {}

    private static synchronized PickupTransactionJournal journal(ServerLevel level) throws IOException {
        MinecraftServer server = level.getServer();
        if (BLOCKED.containsKey(server))
            throw new IOException("pickup evidence journal fail closed: " + BLOCKED.get(server));
        PickupTransactionJournal existing = OPEN.get(server);
        if (existing != null) return existing;
        Path path = server.getWorldPath(LevelResource.ROOT)
            .resolve("data").resolve("hearthbound").resolve("pickup-extraction-v1.bin");
        try {
            PickupTransactionJournal opened = new PickupTransactionJournal(
                path, HearthboundWorldIdentity.get(level));
            OPEN.put(server, opened);
            return opened;
        } catch (IOException | RuntimeException failure) {
            BLOCKED.put(server, failure.getClass().getSimpleName());
            throw new IOException("pickup evidence journal unavailable", failure);
        }
    }

    static synchronized void beforeExtraction(ServerLevel level,
            PickupTransactionJournal.Intent intent) throws IOException {
        try {
            journal(level).begin(intent);
        } catch (IOException | RuntimeException failure) {
            BLOCKED.put(level.getServer(), failure.getClass().getSimpleName());
            throw new IOException("cannot durably start pickup", failure);
        }
    }

    static synchronized void afterExtraction(ServerLevel level, UUID job,
            boolean empty) throws IOException {
        try {
            journal(level).finish(job, empty
                ? PickupTransactionJournal.State.EXTRACTION_EMPTY
                : PickupTransactionJournal.State.CARGO_RETURNED);
        } catch (IOException | RuntimeException failure) {
            BLOCKED.put(level.getServer(), failure.getClass().getSimpleName());
            throw new IOException("cannot durably finish pickup", failure);
        }
    }

    /**
     * A recovered UNRESOLVED entry may represent a call that happened before
     * a crash. Never infer whether source inventory changed.
     */
    static synchronized PickupTransactionJournal.View inspect(ServerLevel level,
            UUID job) throws IOException {
        return journal(level).inspect(job);
    }

    static synchronized void serverStopped(MinecraftServer server) {
        PickupTransactionJournal opened = OPEN.remove(server);
        BLOCKED.remove(server);
        if (opened != null) {
            try { opened.close(); }
            catch (IOException failure) {
                // The journal will be CRC/hash checked on the next startup.
                System.err.println("Hearthbound pickup journal close failed: " + failure);
            }
        }
    }
}
