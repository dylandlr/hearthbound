package dev.hearthbound.world;

import dev.hearthbound.research.AutonomousLibraryStudy;
import dev.hearthbound.research.LibraryStudyRuntime;
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
        if (!level.hasChunkAt(source) || !level.hasChunkAt(destination)
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

    public static void enable(Villager citizen, boolean enabled) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (enabled && (!tag.contains("source") || !tag.contains("destination")
                || !tag.contains("library")))
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
        if (now < tag.getLong("retryAfter") || SableHauling.active(citizen)
                || AutonomousLibraryStudy.active(citizen)
                || LibraryStudyRuntime.state(citizen) == LibraryStudyRuntime.State.STUDYING)
            return;
        if (!level.dimension().location().toString().equals(tag.getString("dimension")))
            return;
        BlockPos source = BlockPos.of(tag.getLong("source"));
        BlockPos destination = BlockPos.of(tag.getLong("destination"));
        BlockPos library = BlockPos.of(tag.getLong("library"));
        // Fail closed on unloaded chunks. Never force-load for an autonomous job.
        if (!level.hasChunkAt(source) || !level.hasChunkAt(destination)
                || !level.hasChunkAt(library)) return;
        String outcome = SableWorkChoice.consider(level, citizen, source, destination, library);
        if (!outcome.endsWith("_ASSIGNED")) tag.putLong("retryAfter", now + COOLDOWN);
    }

    public static String inspect(Villager citizen) {
        CompoundTag t = citizen.getPersistentData().getCompound(KEY);
        return "AUTO_WORK enabled=" + enabled(citizen)
                + " configured=" + t.contains("source")
                + " retryAfter=" + t.getLong("retryAfter");
    }
}
