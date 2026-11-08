package dev.hearthbound.world;

import dev.hearthbound.evidence.PickupFailureContract;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;

/**
 * Citizen-owned persistent negative motor experiences. ONLY the real hauling
 * extraction branch writes these, never a read-only inventory probe, blocked
 * route, source-claim failure, or an LLM/operating command.
 *
 * This is villager Saved NBT, not a crash-durable fsync journal. If malformed
 * or saturated, new policy decisions fail closed instead of forgetting misses.
 */
public final class SourceFailureBeliefs {
    private static final String ROOT = "hearthbound.pickupFailures.v1";
    private static final String ENTRIES = "entries";
    private static final int LIMIT = 32;
    private static final String HAUL = "hearthbound.haul";
    private static final String ASSIGNMENT = "reportPolicyDispatch.v1";
    private SourceFailureBeliefs() {}

    private static String sourceKey(ServerLevel level, BlockPos source) {
        return level.dimension().location() + "|" + source.getX() + ","
            + source.getY() + "," + source.getZ();
    }

    private static boolean validRoot(CompoundTag root) {
        return PickupFailureContract.SCHEMA.equals(root.getString("schema"))
            && !root.getBoolean("saturated");
    }

    private static CompoundTag invalidFailClosed(Villager executor) {
        CompoundTag root = executor.getPersistentData().getCompound(ROOT);
        root.putString("schema", PickupFailureContract.SCHEMA);
        root.putBoolean("saturated", true);
        executor.getPersistentData().put(ROOT, root);
        return root;
    }

    /**
     * Called immediately AFTER extractWheat returned ItemStack.EMPTY and
     * before SableHauling transitions to PAUSED. It never reads the chest.
     * Non-policy legacy tasks remain outside this experimental contract.
     */
    public static void recordAfterEmptyExtraction(ServerLevel level, Villager executor,
                                                  BlockPos actualSource, CompoundTag haul) {
        if (level == null || executor == null || actualSource == null || haul == null
                || !haul.contains(ASSIGNMENT)) return;
        if (!haul.hasUUID("jobId") || !haul.contains("assignedTick")
                || !haul.contains("source") || haul.getLong("source") != actualSource.asLong()
                || haul.contains("cargo")) {
            invalidFailClosed(executor);
            return;
        }
        CompoundTag assignment = haul.getCompound(ASSIGNMENT);
        UUID job = haul.getUUID("jobId");
        UUID world = HearthboundWorldIdentity.get(level);
        String observedSource = sourceKey(level, actualSource);
        long assigned = haul.getLong("assignedTick");
        long tick = level.getGameTime();
        if (!assignment.hasUUID("job") || !assignment.hasUUID("world")
                || !assignment.hasUUID("executor") || !assignment.hasUUID("recipient")
                || !job.equals(assignment.getUUID("job"))
                || !world.equals(assignment.getUUID("world"))
                || !executor.getUUID().equals(assignment.getUUID("executor"))
                || !executor.getUUID().equals(assignment.getUUID("recipient"))
                || assignment.getLong("source") != actualSource.asLong()
                || assignment.getLong("assignedTick") != assigned
                || assignment.getLong("decisionTick") > assigned
                || assigned > tick || assignment.getString("reportId").isBlank()) {
            invalidFailClosed(executor);
            return;
        }
        PickupFailureContract.Failure negative;
        try {
            negative = new PickupFailureContract.Failure(world, job, executor.getUUID(),
                observedSource, assignment.getString("reportId"), assigned, tick,
                PickupFailureContract.OBSERVATION);
        } catch (IllegalArgumentException invalid) {
            invalidFailClosed(executor);
            return;
        }
        boolean existed = executor.getPersistentData().contains(ROOT);
        CompoundTag root = executor.getPersistentData().getCompound(ROOT);
        if (existed && !validRoot(root)) {
            invalidFailClosed(executor);
            return;
        }
        ListTag entries = root.getList(ENTRIES, Tag.TAG_COMPOUND);
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag r = entries.getCompound(i);
            if (r.hasUUID("job") && job.equals(r.getUUID("job"))) {
                // Re-running the same failed job must not create a new
                // observation timestamp, allowing stale evidence to revive.
                return;
            }
        }
        if (entries.size() >= LIMIT) {
            invalidFailClosed(executor);
            return;
        }
        CompoundTag row = new CompoundTag();
        row.putString("schema", PickupFailureContract.SCHEMA);
        row.putUUID("world", negative.world());
        row.putUUID("job", negative.job());
        row.putUUID("executor", negative.executor());
        row.putString("source", negative.source());
        row.putString("reportId", negative.selectedReportId());
        row.putLong("assignedTick", negative.assignedTick());
        row.putLong("failedTick", negative.failedTick());
        row.putString("observation", negative.observation());
        entries.add(row);
        root.putString("schema", PickupFailureContract.SCHEMA);
        root.put(ENTRIES, entries);
        executor.getPersistentData().put(ROOT, root);
    }

    private static PickupFailureContract.Failure decode(CompoundTag row) {
        if (!PickupFailureContract.SCHEMA.equals(row.getString("schema"))
                || !row.hasUUID("world") || !row.hasUUID("job")
                || !row.hasUUID("executor") || !row.contains("source")
                || !row.contains("reportId") || !row.contains("assignedTick")
                || !row.contains("failedTick") || !row.contains("observation"))
            throw new IllegalArgumentException("missing physical extraction evidence");
        return new PickupFailureContract.Failure(row.getUUID("world"),
            row.getUUID("job"), row.getUUID("executor"),
            row.getString("source"), row.getString("reportId"),
            row.getLong("assignedTick"), row.getLong("failedTick"),
            row.getString("observation"));
    }

    /**
     * Filter recipient report memory after a real failed pickup. New direct
     * observation made AFTER the failed tick is allowed (if delivered);
     * older reports from any sender cannot be silently replayed.
     */
    public static boolean acceptsReport(ServerLevel level, Villager executor,
                                        BlockPos source, CompoundTag report) {
        if (level == null || executor == null || source == null || report == null)
            return false;
        if (!executor.getPersistentData().contains(ROOT)) return true;
        CompoundTag root = executor.getPersistentData().getCompound(ROOT);
        if (!validRoot(root)) return false;
        ListTag entries = root.getList(ENTRIES, Tag.TAG_COMPOUND);
        PickupFailureContract.Report candidate;
        try {
            candidate = new PickupFailureContract.Report(
                report.getString("source"), report.getString("id"),
                report.getLong("observed_tick"), report.getLong("delivered_tick"));
        } catch (IllegalArgumentException invalid) {
            return false;
        }
        UUID world=HearthboundWorldIdentity.get(level);
        for (int i = 0; i < entries.size(); i++) {
            try {
                PickupFailureContract.Failure failure=decode(entries.getCompound(i));
                if (PickupFailureContract.disqualifies(
                        failure, world, executor.getUUID(), candidate)) return false;
            } catch (IllegalArgumentException invalid) {
                return false;
            }
        }
        return true;
    }

    public static String inspect(ServerLevel level, Villager executor, BlockPos source) {
        final String base = "PICKUP_FAILURE_BELIEF schema=" + PickupFailureContract.SCHEMA
            + " source=" + sourceKey(level, source)
            + " executor=" + executor.getUUID()
            + " inventory_read=false evidence_origin=REAL_EXTRACTION_ONLY"
            + " research_authorized=false reward_authorized=false";
        if (!executor.getPersistentData().contains(ROOT))
            return base + " state=NONE next=NONE";
        CompoundTag root=executor.getPersistentData().getCompound(ROOT);
        if (!validRoot(root))
            return base + " state=FAIL_CLOSED next=OPERATOR_REVIEW";
        ListTag entries=root.getList(ENTRIES,Tag.TAG_COMPOUND);
        PickupFailureContract.Failure newest=null;
        for (int i=0;i<entries.size();i++) {
            PickupFailureContract.Failure negative;
            try { negative=decode(entries.getCompound(i)); }
            catch (IllegalArgumentException invalid) {
                return base + " state=FAIL_CLOSED next=OPERATOR_REVIEW";
            }
            if (negative.world().equals(HearthboundWorldIdentity.get(level))
                    && negative.executor().equals(executor.getUUID())
                    && negative.source().equals(sourceKey(level, source))
                    && (newest==null || negative.failedTick()>newest.failedTick()))
                newest=negative;
        }
        if (newest==null) return base+" state=NONE next=NONE";
        return base + " state=PICKUP_RETURNED_EMPTY"
            + " job="+newest.job()
            + " failed_tick="+newest.failedTick()
            + " assigned_tick="+newest.assignedTick()
            + " report_id="+newest.selectedReportId()
            + " next=REQUEST_REOBSERVATION"
            + " source_empty_verified=false physical_delivery_verified=false";
    }
}
