package dev.hearthbound.world;

import dev.hearthbound.ai.WorkOfferLifecycle;
import dev.hearthbound.research.AutonomousLibraryStudy;
import dev.hearthbound.research.LibraryStudyRuntime;
import dev.hearthbound.research.LibraryCandidateDiscovery;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/** Opt-in, operator-configured two-offer decision loop for test citizens. */
public final class SableAutoWork {
    private static final String KEY = "hearthbound.sableAutoWorkV1";
    private static final long INTERVAL = 200;
    private static final long COOLDOWN = 600;
    private SableAutoWork() {}

    public static void configure(ServerLevel level, Villager citizen,
                                 BlockPos source, BlockPos destination, BlockPos library) {
        if (citizen.level() != level || source.equals(destination))
            throw new IllegalArgumentException("Invalid world or endpoints");
        if ((source != null && !level.hasChunkAt(source)) || !level.hasChunkAt(destination)
                || !level.hasChunkAt(library))
            throw new IllegalArgumentException("All configured chunks must be loaded");
        CompoundTag tag = new CompoundTag();
        tag.putString("dimension", level.dimension().location().toString());
        tag.putLong("source", source.asLong());
        tag.putLong("destination", destination.asLong());
        tag.putLong("library", library.asLong());
        tag.putBoolean("enabled", false);
        citizen.getPersistentData().put(KEY, tag);
    }

    /** Haul locations remain operator-authorized; library is discovered nearby. */
    public static void configureDiscover(ServerLevel level, Villager citizen,
                                         BlockPos source, BlockPos destination) {
        if (citizen.level() != level || source.equals(destination)
                || !level.hasChunkAt(source) || !level.hasChunkAt(destination))
            throw new IllegalArgumentException("Invalid or unloaded hauling endpoints");
        CompoundTag tag = new CompoundTag();
        tag.putString("dimension", level.dimension().location().toString());
        tag.putLong("source", source.asLong());
        tag.putLong("destination", destination.asLong());
        tag.putBoolean("discoverLibrary", true);
        tag.putBoolean("enabled", false);
        citizen.getPersistentData().put(KEY, tag);
    }

    /** Discover nearby wheat sources; operator explicitly authorizes destination. */
    public static void configureSourceDiscovery(ServerLevel level, Villager citizen,
                                                BlockPos destination) {
        if (citizen.level() != level || !level.hasChunkAt(destination))
            throw new IllegalArgumentException("Destination must be in a loaded citizen dimension");
        CompoundTag tag = new CompoundTag();
        tag.putString("dimension", level.dimension().location().toString());
        tag.putLong("destination", destination.asLong());
        tag.putBoolean("discoverSource", true);
        tag.putBoolean("discoverLibrary", true);
        tag.putBoolean("enabled", false);
        citizen.getPersistentData().put(KEY, tag);
    }

    public static void enable(Villager citizen, boolean enabled) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (enabled && ((!tag.contains("source") && !tag.getBoolean("discoverSource")) || !tag.contains("destination")
                || (!tag.getBoolean("discoverLibrary") && !tag.contains("library"))))
            throw new IllegalStateException("Configure endpoints first");
        tag.putBoolean("enabled", enabled);
        citizen.getPersistentData().put(KEY, tag);
    }

    public static boolean enabled(Villager citizen) {
        return citizen.getPersistentData().getCompound(KEY).getBoolean("enabled");
    }

    public static void tick(ServerLevel level, Villager citizen) {
        if (!enabled(citizen)) return;
        long now = level.getGameTime();
        if (Math.floorMod(now, INTERVAL) != Math.floorMod(citizen.getUUID().hashCode(), INTERVAL))
            return;
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        // A prior assignment is not a successful delivery. Only the exact
        // completed, cargo-free job with matching endpoint earns that status.
        if (tag.hasUUID("haulJob") && !tag.getBoolean("haulCompleted")) {
            java.util.UUID expected = tag.getUUID("haulJob");
            BlockPos expectedDestination = BlockPos.of(tag.getLong("destination"));
            if (SableHauling.completedJob(citizen, expected, expectedDestination))
                tag.putBoolean("haulCompleted", true);
        }
        if (!WorkOfferLifecycle.canAdvance(tag.getBoolean("haulIssued"),
                tag.getBoolean("haulCompleted"))) return;
        if (now < tag.getLong("retryAfter") || SableHauling.active(citizen)
                || AutonomousLibraryStudy.active(citizen)
                || LibraryStudyRuntime.state(citizen) == LibraryStudyRuntime.State.STUDYING)
            return;
        if (!level.dimension().location().toString().equals(tag.getString("dimension")))
            return;
        BlockPos source = tag.getBoolean("discoverSource")
                ? WheatSourceDiscovery.nearest(level, citizen, BlockPos.of(tag.getLong("destination")))
                : BlockPos.of(tag.getLong("source"));
        BlockPos destination = BlockPos.of(tag.getLong("destination"));
        BlockPos library = tag.getBoolean("discoverLibrary")
                ? LibraryCandidateDiscovery.nearest(level, citizen)
                : BlockPos.of(tag.getLong("library"));
        // Fail closed on unloaded chunks. Never force-load for an autonomous job.
        if (!level.hasChunkAt(source) || !level.hasChunkAt(destination)
                || (library != null && !level.hasChunkAt(library))) return;
        String outcome = SableWorkChoice.consider(level, citizen, source, destination, library,
                !tag.getBoolean("haulIssued"));
        if ("HAUL_ASSIGNED".equals(outcome)) {
            java.util.UUID job = SableHauling.jobId(citizen);
            if (job != null) {
                tag.putUUID("haulJob", job);
                tag.putBoolean("haulIssued", true);
                tag.putBoolean("haulCompleted", false);
            }
        }
        if (!outcome.endsWith("_ASSIGNED")) tag.putLong("retryAfter", now + COOLDOWN);
    }

    public static String inspect(Villager citizen) {
        CompoundTag t = citizen.getPersistentData().getCompound(KEY);
        return "AUTO_WORK enabled=" + enabled(citizen)
                + " configured=" + t.contains("source")
                + " discoverLibrary=" + t.getBoolean("discoverLibrary")
                + " discoverSource=" + t.getBoolean("discoverSource")
                + " haulIssued=" + t.getBoolean("haulIssued")
                + " haulCompleted=" + t.getBoolean("haulCompleted")
                + " haulJob=" + (t.hasUUID("haulJob") ? t.getUUID("haulJob") : "none")
                + " retryAfter=" + t.getLong("retryAfter");
    }
}
