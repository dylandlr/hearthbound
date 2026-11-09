package dev.hearthbound.world;

import dev.hearthbound.evidence.PickupTransactionJournal;
import dev.hearthbound.evidence.PickupJournalOwnership;
import dev.hearthbound.evidence.PickupCitizenReconciliation;
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
        Path directory = server.getWorldPath(LevelResource.ROOT)
            .resolve("data").resolve("hearthbound");
        try {
            PickupTransactionJournal opened = PickupJournalOwnership.open(
                directory, HearthboundWorldIdentity.get(level));
            OPEN.put(server, opened);
            return opened;
        } catch (IOException | RuntimeException failure) {
            BLOCKED.put(server, failure.getClass().getSimpleName());
            throw new IOException("pickup evidence journal unavailable", failure);
        }
    }

    /** Eagerly verify ownership and all frames before the first citizen tick. */
    static synchronized void startup(ServerLevel level) throws IOException {
        journal(level);
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

    /**
     * Read-only audit of persisted pickup transactions. Does not enumerate
     * villager NBT or touch source/destination chunks, and never reconciles
     * physical inventories. Includes intents for unloaded citizens.
     */
    static synchronized String audit(ServerLevel level, int limit) {
        try {
            java.util.List<PickupTransactionJournal.View> all = journal(level).snapshot();
            int unresolved = 0, empty = 0, cargo = 0;
            for (PickupTransactionJournal.View view : all) {
                switch (view.state()) {
                    case UNRESOLVED -> unresolved++;
                    case EXTRACTION_EMPTY -> empty++;
                    case CARGO_RETURNED -> cargo++;
                }
            }
            StringBuilder result = new StringBuilder(
                "PICKUP_JOURNAL_AUDIT status=READ_ONLY world="
                + HearthboundWorldIdentity.get(level)
                + " total=" + all.size() + " unresolved=" + unresolved
                + " extraction_empty=" + empty + " cargo_returned=" + cargo
                + " chunk_load=false nbt_scan=false inventory_read=false"
                + " reward_authorized=false task_authorized=false");
            int shown = 0;
            for (PickupTransactionJournal.View view : all) {
                if (view.state() != PickupTransactionJournal.State.UNRESOLVED)
                    continue;
                if (shown++ >= Math.max(0, Math.min(limit, 16))) break;
                result.append(" pending_").append(shown).append("=")
                    .append(view.intent().job()).append(",")
                    .append(view.intent().executor()).append(",")
                    .append(view.intent().attemptedTick());
            }
            return result.toString();
        } catch (IOException | RuntimeException failure) {
            return "PICKUP_JOURNAL_AUDIT status=FAIL_CLOSED"
                + " inventory_read=false task_authorized=false"
                + " reward_authorized=false";
        }
    }

    /**
     * Read-only join with only currently loaded villager NBT. Does not call
     * getChunk, load region/entity files, or read source inventories. Missing
     * entities remain NOT_LOADED; contradictions cannot authorize actions.
     */
    static synchronized String auditLoadedCitizens(ServerLevel level) {
        try {
            java.util.List<PickupTransactionJournal.View> recorded = journal(level).snapshot();
            java.util.List<PickupCitizenReconciliation.Citizen> loaded =
                new java.util.ArrayList<>();
            for (ServerLevel current : level.getServer().getAllLevels()) {
                for (net.minecraft.world.entity.Entity entity : current.getAllEntities()) {
                    if (!(entity instanceof net.minecraft.world.entity.npc.Villager citizen)
                            || !citizen.getPersistentData().getBoolean("hearthbound.sable"))
                        continue;
                    net.minecraft.nbt.CompoundTag haul =
                        citizen.getPersistentData().getCompound("hearthbound.haul");
                    UUID savedJob = haul.hasUUID("jobId") ? haul.getUUID("jobId") : null;
                    loaded.add(new PickupCitizenReconciliation.Citizen(
                        citizen.getUUID(), savedJob, haul.contains("reportPolicyDispatch.v1"),
                        haul.contains("cargo"), haul.getInt("phase") == 4));
                }
            }
            PickupCitizenReconciliation.Summary result =
                PickupCitizenReconciliation.inspect(recorded, loaded);
            return "PICKUP_CITIZEN_AUDIT status=READ_ONLY"
                + " journal_jobs=" + result.rows().size()
                + " loaded_citizens=" + loaded.size()
                + " not_loaded=" + result.notLoaded()
                + " mismatched=" + result.mismatched()
                + " hold_for_review=" + result.heldForReview()
                + " nbt_scan=LOADED_ONLY chunk_load=false"
                + " inventory_read=false task_authorized=false reward_authorized=false";
        } catch (IOException | RuntimeException failure) {
            return "PICKUP_CITIZEN_AUDIT status=FAIL_CLOSED"
                + " task_authorized=false reward_authorized=false";
        }
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
