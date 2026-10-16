package dev.hearthbound.research;

import dev.hearthbound.world.SableHauling;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Opt-in, server-tick study job. Does not teleport citizens or grant knowledge;
 * movement is performed by vanilla navigation and study remains physically checked.
 */
public final class AutonomousLibraryStudy {
    private static final String KEY = "hearthbound.autonomousLibraryV1";
    private static final int MAX_DISTANCE_SQUARED = 64 * 64;
    private static final int MAX_TRAVEL_TICKS = 2400;
    private static final int LITERACY = 60; // Development baseline until citizen literacy is modeled.

    private AutonomousLibraryStudy() {}

    public static void assign(ServerLevel level, Villager citizen, BlockPos library) {
        if (citizen.level() != level) throw new IllegalArgumentException("Citizen not in this dimension");
        if (!level.hasChunkAt(library)) throw new IllegalStateException("Library chunk not loaded");
        if (citizen.distanceToSqr(library.getX() + .5, library.getY() + .5, library.getZ() + .5)
                > MAX_DISTANCE_SQUARED) throw new IllegalArgumentException("Library is too distant");
        if (SableHauling.active(citizen)) throw new IllegalStateException("Citizen has a hauling assignment");
        if (LibraryStudyRuntime.state(citizen) == LibraryStudyRuntime.State.STUDYING)
            throw new IllegalStateException("Citizen is already studying");
        CompoundTag tag = new CompoundTag();
        tag.putString("dimension", level.dimension().location().toString());
        tag.putLong("library", library.asLong());
        tag.putLong("assignedTick", level.getGameTime());
        tag.putString("state", "TRAVELING");
        citizen.getPersistentData().put(KEY, tag);
    }

    public static void tick(ServerLevel level, Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        if (!"TRAVELING".equals(tag.getString("state"))) return;
        if (!level.dimension().location().toString().equals(tag.getString("dimension"))
                || level.getGameTime() < tag.getLong("assignedTick")
                || level.getGameTime() - tag.getLong("assignedTick") > MAX_TRAVEL_TICKS
                || SableHauling.active(citizen)) {
            tag.putString("state", "INTERRUPTED");
            return;
        }
        BlockPos library = BlockPos.of(tag.getLong("library"));
        if (!level.hasChunkAt(library)) return;
        double distance = citizen.distanceToSqr(
                library.getX() + .5, library.getY() + .5, library.getZ() + .5);
        if (distance > 9) {
            if (level.getGameTime() % 20 == 0)
                citizen.getNavigation().moveTo(library.getX() + .5, library.getY(),
                        library.getZ() + .5, .75);
            return;
        }
        try {
            LibraryStudyRuntime.begin(level, citizen, library, LITERACY);
            tag.putString("state", "STUDYING");
        } catch (IllegalStateException | IllegalArgumentException ex) {
            tag.putString("state", "INTERRUPTED");
        }
    }

    public static String inspect(Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        String state = tag.getString("state");
        if ("STUDYING".equals(state)) {
            state = switch (LibraryStudyRuntime.state(citizen)) {
                case COMPLETED -> "COMPLETED";
                case INTERRUPTED -> "INTERRUPTED";
                default -> state;
            };
        }
        return "AUTONOMOUS_LIBRARY " + (state.isEmpty() ? "UNASSIGNED" : state);
    }
}
