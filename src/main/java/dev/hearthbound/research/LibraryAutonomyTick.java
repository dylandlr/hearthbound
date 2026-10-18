package dev.hearthbound.research;

import dev.hearthbound.world.SableHauling;
import dev.hearthbound.world.SableAutoWork;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Opt-in library routine with a bounded scan and cooldown.
 * The server scans only loaded blocks in a small radius. It never force-loads
 * chunks or guesses at inventory contents.
 */
public final class LibraryAutonomyTick {
    private static final String KEY = "hearthbound.libraryAutoV1";
    private static final int SCAN_RADIUS = 8;
    private static final long DECISION_INTERVAL = 200;
    private static final long FAILURE_COOLDOWN = 600;

    private LibraryAutonomyTick() {}

    public static void setEnabled(Villager citizen, boolean enabled) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        tag.putBoolean("enabled", enabled);
        citizen.getPersistentData().put(KEY, tag);
    }

    public static boolean enabled(Villager citizen) {
        return citizen.getPersistentData().getCompound(KEY).getBoolean("enabled");
    }

    public static void tick(ServerLevel level, Villager citizen) {
        if (SableAutoWork.enabled(citizen)) return; // Single active autonomous scheduler.
        if (!enabled(citizen) || level.getGameTime() % DECISION_INTERVAL
                != Math.floorMod(citizen.getUUID().hashCode(), (int) DECISION_INTERVAL)) return;
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        long now = level.getGameTime();
        CitizenDecisionCadence.WorkState workState;
        if (SableHauling.active(citizen)) {
            workState = CitizenDecisionCadence.WorkState.HAULING;
        } else if (AutonomousLibraryStudy.active(citizen)) {
            workState = LibraryStudyRuntime.state(citizen) == LibraryStudyRuntime.State.STUDYING
                    ? CitizenDecisionCadence.WorkState.STUDYING
                    : CitizenDecisionCadence.WorkState.TRAVELING;
        } else {
            workState = switch (LibraryStudyRuntime.state(citizen)) {
                case STUDYING -> CitizenDecisionCadence.WorkState.STUDYING;
                case COMPLETED -> CitizenDecisionCadence.WorkState.COMPLETED;
                case INTERRUPTED -> CitizenDecisionCadence.WorkState.INTERRUPTED;
                default -> CitizenDecisionCadence.WorkState.IDLE;
            };
        }
        var snapshot = new CitizenDecisionCadence.Snapshot(
                enabled(citizen), LibraryPolicyBridge.studyPriority(citizen),
                CitizenTechnologyKnowledge.knows(citizen, LibraryStudyRuntime.RECIPE),
                SableHauling.active(citizen), workState, now, tag.getLong("retryAfter"));
        if (!CitizenDecisionCadence.shouldConsider(snapshot)) return;

        BlockPos origin = citizen.blockPosition();
        BlockPos candidate = null;
        double nearest = Double.POSITIVE_INFINITY;
        for (BlockPos pos : BlockPos.betweenClosed(
                origin.offset(-SCAN_RADIUS,-2,-SCAN_RADIUS),
                origin.offset(SCAN_RADIUS,2,SCAN_RADIUS))) {
            if (!level.hasChunkAt(pos)) continue;
            if (!LibraryStudyRuntime.hasBook(level, pos)) continue;
            double distance = pos.distSqr(origin);
            if (distance < nearest) {
                candidate = pos.immutable();
                nearest = distance;
            }
        }
        if (candidate == null) {
            tag.putLong("retryAfter", now + FAILURE_COOLDOWN);
            return;
        }
        try {
            if (!LibraryPolicyBridge.consider(level, citizen, candidate))
                tag.putLong("retryAfter", now + FAILURE_COOLDOWN);
        } catch (IllegalStateException | IllegalArgumentException ex) {
            tag.putLong("retryAfter", now + FAILURE_COOLDOWN);
        }
    }
}
