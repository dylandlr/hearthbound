package dev.hearthbound.world;

import dev.hearthbound.evidence.PickupFailureContract;
import java.util.UUID;
import java.util.HashSet;
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
    private static final String ASSIGNMENT = "reportPolicyDispatch.v1";
    private static final String REQUEST = "hearthbound.pendingSourceRecheck.v1";
    private SourceFailureBeliefs() {}

    private static String sourceKey(ServerLevel level, BlockPos source) {
        return level.dimension().location() + "|" + source.getX() + ","
            + source.getY() + "," + source.getZ();
    }

    private static boolean validRoot(CompoundTag root) {
        if (!PickupFailureContract.SCHEMA.equals(root.getString("schema"))
                || !(root.get(ENTRIES) instanceof ListTag entries)
                || (root.contains("saturated") && !root.contains("saturated", Tag.TAG_BYTE))
                || root.getBoolean("saturated") || entries.size() > LIMIT) return false;
        // An NBT list with a non-compound element type must not silently be
        // parsed as an empty compound list, resurrecting invalidated reports.
        return entries.isEmpty() || entries.getElementType() == Tag.TAG_COMPOUND;
    }

    /** Never interpret foreign, future, duplicate or malformed events as no failure. */
    private static boolean validContext(ServerLevel level, Villager executor) {
        if (executor.level() != level) return false;
        if (!executor.getPersistentData().contains(ROOT))
            return !executor.getPersistentData().contains(REQUEST);
        CompoundTag root = executor.getPersistentData().getCompound(ROOT);
        if (!validRoot(root)) return false;
        ListTag entries = root.getList(ENTRIES, Tag.TAG_COMPOUND);
        var jobs = new HashSet<UUID>();
        PickupFailureContract.Failure requested = null;
        CompoundTag pending = executor.getPersistentData().getCompound(REQUEST);
        for (int i = 0; i < entries.size(); i++) {
            try {
                var failure = decode(entries.getCompound(i));
                if (!PickupFailureContract.validInContext(failure,
                        HearthboundWorldIdentity.get(level), executor.getUUID(), level.getGameTime())
                        || !jobs.add(failure.job())) return false;
                if (pending.hasUUID("failedJob") && failure.job().equals(pending.getUUID("failedJob")))
                    requested = failure;
            } catch (IllegalArgumentException invalid) { return false; }
        }
        if (!executor.getPersistentData().contains(REQUEST)) return true;
        if (requested == null
                || !"hearthbound.reobservation-request.v1".equals(pending.getString("schema"))
                || !pending.hasUUID("world") || !requested.world().equals(pending.getUUID("world"))
                || !pending.hasUUID("recipient") || !executor.getUUID().equals(pending.getUUID("recipient"))
                || !pending.contains("source", Tag.TAG_LONG)
                || !requested.source().equals(sourceKey(level, BlockPos.of(pending.getLong("source"))))
                || !pending.contains("failedTick", Tag.TAG_LONG)
                || pending.getLong("failedTick") != requested.failedTick()
                || !requested.selectedReportId().equals(pending.getString("invalidatedReportId"))
                || !pending.contains("requestTick", Tag.TAG_LONG)
                || pending.getLong("requestTick") < requested.failedTick()
                || pending.getLong("requestTick") > level.getGameTime()) return false;
        if ("AWAITING_SCOUT_DIRECT_OBSERVATION".equals(pending.getString("state")))
            return !pending.contains("reportId") && !pending.contains("observedTick")
                && !pending.contains("deliveredTick");
        return "FULFILLED_BY_NEW_DIRECT_REPORT".equals(pending.getString("state"))
            && !pending.getString("reportId").isBlank()
            && !requested.selectedReportId().equals(pending.getString("reportId"))
            && pending.contains("observedTick", Tag.TAG_LONG)
            && pending.contains("deliveredTick", Tag.TAG_LONG)
            && pending.getLong("observedTick") > requested.failedTick()
            && pending.getLong("deliveredTick") >= pending.getLong("observedTick")
            && pending.getLong("deliveredTick") >= pending.getLong("requestTick")
            && pending.getLong("deliveredTick") <= level.getGameTime();
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
        if ((existed || executor.getPersistentData().contains(REQUEST)) && !validContext(level, executor)) {
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
                || !row.hasUUID("executor") || !row.contains("source", Tag.TAG_STRING)
                || !row.contains("reportId", Tag.TAG_STRING) || !row.contains("assignedTick", Tag.TAG_LONG)
                || !row.contains("failedTick", Tag.TAG_LONG) || !row.contains("observation", Tag.TAG_STRING))
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
        if (!SourceReportSession.accepts(level, report, report.getLong("delivered_tick"))
                || !sourceKey(level, source).equals(report.getString("source"))
                || !validContext(level, executor)) return false;
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

    /**
     * Record an explicit citizen-owned request for a physical scout recheck.
     * Bind it to the precise failed Minecraft job; no scout is contacted or
     * chest inspected by this command. The same failed job cannot mint
     * repeated timestamp-shifting requests.
     */
    public static String requestReobservation(ServerLevel level, Villager executor,
                                              BlockPos source) {
        String denied="SOURCE_REOBSERVATION_REQUEST status=DENIED"
            +" reward_authorized=false learning_authorized=false NO_RESEARCH_CREDIT";
        if (level == null || executor == null || source == null
                || executor.level()!=level || !CitizenSourceKnowledge.isCitizen(executor)
                || !executor.getPersistentData().contains(ROOT))
            return denied+" reason=NO_PHYSICAL_FAILED_PICKUP";
        CompoundTag root=executor.getPersistentData().getCompound(ROOT);
        if (!validContext(level, executor)) return denied+" reason=FAIL_CLOSED_EVIDENCE";
        PickupFailureContract.Failure newest=null;
        ListTag failures=root.getList(ENTRIES,Tag.TAG_COMPOUND);
        UUID world=HearthboundWorldIdentity.get(level);
        for (int i=0;i<failures.size();i++) {
            PickupFailureContract.Failure attempt;
            try { attempt=decode(failures.getCompound(i)); }
            catch (IllegalArgumentException malformed) {
                return denied+" reason=MALFORMED_FAILED_PICKUP";
            }
            if (!attempt.world().equals(world)
                    || !attempt.executor().equals(executor.getUUID())
                    || !attempt.source().equals(sourceKey(level,source))) continue;
            if (newest==null || attempt.failedTick()>newest.failedTick())
                newest=attempt;
        }
        if (newest==null) return denied+" reason=NO_PHYSICAL_FAILED_PICKUP";
        if (executor.getPersistentData().contains(REQUEST)) {
            CompoundTag existing=executor.getPersistentData().getCompound(REQUEST);
            if ("AWAITING_SCOUT_DIRECT_OBSERVATION".equals(existing.getString("state")))
                return denied+" reason=ALREADY_AWAITING_SCOUT"
                    +" failed_job="+existing.getUUID("failedJob");
            if (newest.job().equals(existing.getUUID("failedJob")))
                return denied+" reason=ALREADY_FULFILLED failed_job="+newest.job();
        }
        CompoundTag pending=new CompoundTag();
        pending.putString("schema","hearthbound.reobservation-request.v1");
        pending.putUUID("world",world);
        pending.putUUID("recipient",executor.getUUID());
        pending.putUUID("failedJob",newest.job());
        pending.putLong("failedTick",newest.failedTick());
        pending.putString("invalidatedReportId",newest.selectedReportId());
        pending.putLong("source",source.asLong());
        pending.putLong("requestTick",level.getGameTime());
        pending.putString("state","AWAITING_SCOUT_DIRECT_OBSERVATION");
        executor.getPersistentData().put(REQUEST,pending);
        return "SOURCE_REOBSERVATION_REQUEST status=REQUESTED"
            +" recipient="+executor.getUUID()
            +" source="+sourceKey(level,source)
            +" failed_job="+newest.job()
            +" failed_tick="+newest.failedTick()
            +" request_tick="+level.getGameTime()
            +" origin=FAILED_PHYSICAL_EXTRACTION"
            +" scout_assigned=false scout_observed=false"
            +" task_authorized=false reward_authorized=false NO_RESEARCH_CREDIT";
    }

    /**
     * A source re-observation request is fulfilled only by an actually
     * delivered, *newer direct* report, never by changing hidden inventory
     * or by the same stale report being re-delivered.
     */
    public static boolean fulfillAfterExplicitShare(ServerLevel level, Villager recipient,
                                                    BlockPos source, CompoundTag report) {
        if (level == null || recipient == null || source == null || report == null
                || !recipient.getPersistentData().contains(REQUEST)
                || !recipient.getPersistentData().contains(ROOT)
                || !validContext(level, recipient)
                || !SourceReportSession.accepts(level, report, report.getLong("delivered_tick"))) return false;
        CompoundTag pending=recipient.getPersistentData().getCompound(REQUEST);
        if (!"hearthbound.reobservation-request.v1".equals(pending.getString("schema"))
                || !pending.hasUUID("world")
                || !pending.getUUID("world").equals(HearthboundWorldIdentity.get(level))
                || !pending.hasUUID("recipient")
                || !pending.getUUID("recipient").equals(recipient.getUUID())
                || !pending.hasUUID("failedJob")
                || !pending.contains("failedTick")
                || pending.getLong("source")!=source.asLong()
                || !"AWAITING_SCOUT_DIRECT_OBSERVATION".equals(pending.getString("state"))
                || !"REPORTED_DIRECT_FORGE_OBSERVATION".equals(report.getString("origin"))
                || !sourceKey(level,source).equals(report.getString("source"))
                || !report.hasUUID("sender")
                || report.getUUID("sender").equals(recipient.getUUID())
                || !report.hasUUID("recipient")
                || !report.getUUID("recipient").equals(recipient.getUUID())
                || report.getString("id").isBlank()) return false;
        CompoundTag root=recipient.getPersistentData().getCompound(ROOT);
        if (!validRoot(root)) return false;
        ListTag events=root.getList(ENTRIES,Tag.TAG_COMPOUND);
        long latest=-1;
        UUID latestJob=null;
        for (int i=0;i<events.size();i++) {
            PickupFailureContract.Failure failure;
            try { failure=decode(events.getCompound(i)); }
            catch (IllegalArgumentException invalid) { return false; }
            if (failure.world().equals(HearthboundWorldIdentity.get(level))
                    && failure.executor().equals(recipient.getUUID())
                    && failure.source().equals(sourceKey(level,source))
                    && failure.failedTick()>=latest) {
                latest=failure.failedTick();
                latestJob=failure.job();
            }
        }
        if (latest<0 || !pending.getUUID("failedJob").equals(latestJob)
                || pending.getLong("failedTick")!=latest
                || report.getLong("observed_tick")<=latest
                || report.getString("id").equals(pending.getString("invalidatedReportId"))
                || report.getLong("delivered_tick")<pending.getLong("requestTick")
                || report.getLong("delivered_tick")<report.getLong("observed_tick"))
            return false;
        pending.putString("state","FULFILLED_BY_NEW_DIRECT_REPORT");
        pending.putString("reportId",report.getString("id"));
        pending.putLong("observedTick",report.getLong("observed_tick"));
        pending.putLong("deliveredTick",report.getLong("delivered_tick"));
        recipient.getPersistentData().put(REQUEST,pending);
        return true;
    }

    public static String inspect(ServerLevel level, Villager executor, BlockPos source) {
        final String base = "PICKUP_FAILURE_BELIEF schema=" + PickupFailureContract.SCHEMA
            + " source=" + sourceKey(level, source)
            + " executor=" + executor.getUUID()
            + " world=" + HearthboundWorldIdentity.get(level)
            + " inventory_read=false evidence_origin=REAL_EXTRACTION_ONLY"
            + " research_authorized=false reward_authorized=false";
        if (!validContext(level, executor))
            return base + " state=FAIL_CLOSED next=OPERATOR_REVIEW";
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
        String requestStatus=executor.getPersistentData().contains(REQUEST)
            ? executor.getPersistentData().getCompound(REQUEST).getString("state")
            : "NONE";
        return base + " state=PICKUP_RETURNED_EMPTY"
            + " reobservation_request="+requestStatus
            + " job="+newest.job()
            + " failed_tick="+newest.failedTick()
            + " assigned_tick="+newest.assignedTick()
            + " report_id="+newest.selectedReportId()
            + " next=REQUEST_REOBSERVATION"
            + " source_empty_verified=false physical_delivery_verified=false";
    }
}
