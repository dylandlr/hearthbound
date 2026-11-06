package dev.hearthbound.world;

import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/**
 * Trusted point-of-execution observation of Create's millstone process().
 * A receipt proves a machine processing call, not exclusive provenance of
 * one item in a shared/multi-input machine. No research reward is granted.
 */
public final class MillProcessReceipts extends SavedData {
    private static final org.apache.logging.log4j.Logger LOG =
        org.apache.logging.log4j.LogManager.getLogger("HearthboundMillProcess");
    private static final String NAME = "hearthbound_mill_process_receipts_v1";
    private final java.util.Map<UUID, Receipt> receipts = new java.util.HashMap<>();

    public record Receipt(UUID job, UUID citizen, long pos, long startTick, long tick, int wheatBefore,
                          int wheatAfter, int flourBefore, int flourAfter) {
        /** Older receipts cannot claim verified start time. */
        public Receipt(UUID job, UUID citizen, long pos, long tick, int wheatBefore,
                       int wheatAfter, int flourBefore, int flourAfter) {
            this(job, citizen, pos, -1L, tick, wheatBefore, wheatAfter, flourBefore, flourAfter);
        }
    }

    private MillProcessReceipts() {}

    private static MillProcessReceipts get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(MillProcessReceipts::load, MillProcessReceipts::new, NAME);
    }

    private static MillProcessReceipts load(CompoundTag tag) {
        MillProcessReceipts data = new MillProcessReceipts();
        ListTag entries = tag.getList("receipts", Tag.TAG_COMPOUND);
        for (int i=0;i<entries.size();i++) {
            CompoundTag t=entries.getCompound(i);
            Receipt receipt=new Receipt(t.getUUID("job"), t.getUUID("citizen"), t.getLong("pos"),
                t.contains("startTick") ? t.getLong("startTick") : -1L,
                t.getLong("tick"),t.getInt("wheatBefore"),t.getInt("wheatAfter"),
                t.getInt("flourBefore"),t.getInt("flourAfter"));
            if (data.receipts.putIfAbsent(receipt.job(), receipt)!=null)
                throw new IllegalStateException("Repeated Create processing receipt job UUID");
        }
        return data;
    }

    @Override
    public CompoundTag save(CompoundTag tag) {
        ListTag list = new ListTag();
        receipts.values().stream().sorted((a,b)->a.job().compareTo(b.job())).forEach(receipt -> {
            CompoundTag t=new CompoundTag();
            t.putUUID("job",receipt.job());
            t.putUUID("citizen",receipt.citizen());
            t.putLong("pos",receipt.pos());
            t.putLong("tick",receipt.tick());
            t.putLong("startTick",receipt.startTick());
            t.putInt("wheatBefore",receipt.wheatBefore());
            t.putInt("wheatAfter",receipt.wheatAfter());
            t.putInt("flourBefore",receipt.flourBefore());
            t.putInt("flourAfter",receipt.flourAfter());
            list.add(t);
        });
        tag.put("receipts",list);
        return tag;
    }

    /**
     * Fail-closed at Create's process() entry on a reserved machine.
     * Unreserved Create mills are completely unaffected.
     */
    public static boolean admitProcessing(ServerLevel level, BlockPos pos,
                                          int wheatBefore, int flourBefore) {
        if (!MillReservations.held(level, pos)) return true;
        if (wheatBefore != 1 || flourBefore != 0) {
            MillReservations.taintUnexpectedProcess(level, pos);
            LOG.warn("HEARTHBOUND_PROCESS_VETO unexpected-input pos={} wheat={} flour={}",
                pos, wheatBefore, flourBefore);
            return false;
        }
        var candidates = level.getEntitiesOfClass(net.minecraft.world.entity.npc.Villager.class,
            new net.minecraft.world.phys.AABB(pos).inflate(32),
            citizen -> MillExperimentTrace.matchesAuthorizedProcessing(
                citizen, pos, level.getGameTime(), wheatBefore, flourBefore));
        if (candidates.size() != 1) {
            MillReservations.taintUnexpectedProcess(level, pos);
            LOG.warn("HEARTHBOUND_PROCESS_VETO unauthorized-input pos={} candidates={}",
                pos, candidates.size());
            return false;
        }
        var citizen = candidates.get(0);
        if (!MillReservations.matches(level, pos, MillExperimentTrace.jobId(citizen), citizen.getUUID())) {
            MillReservations.taintUnexpectedProcess(level, pos);
            LOG.warn("HEARTHBOUND_PROCESS_VETO lease-mismatch pos={}", pos);
            return false;
        }
        return true;
    }

    public static void record(ServerLevel level, BlockPos pos, int wheatBefore, int wheatAfter,
                              int flourBefore, int flourAfter) {
        LOG.info("HEARTHBOUND_PROCESS_CALLBACK pos={} tick={} wheat={}->{} flour={}->{}",
            pos, level.getGameTime(), wheatBefore, wheatAfter, flourBefore, flourAfter);
        if (wheatBefore != 1 || wheatAfter != 0 || flourBefore != 0
                || flourAfter <= flourBefore) {
            MillReservations.taintUnexpectedProcess(level, pos);
            LOG.info("HEARTHBOUND_PROCESS_REJECT invalid-transition; reservation tainted if held");
            return;
        }
        // This experimental integration intentionally requires exactly one
        // matching delivered job. Ambiguous ownership means no receipt.
        var candidates = level.getEntitiesOfClass(net.minecraft.world.entity.npc.Villager.class,
            new net.minecraft.world.phys.AABB(pos).inflate(32),
            citizen -> MillExperimentTrace.matchesAuthorizedProcessing(
                citizen, pos, level.getGameTime(), wheatBefore, flourBefore));
        if (candidates.size()!=1) {
            // A real Create process occurred on a reserved machine without
            // exactly one matching authorized delivery. This is compromised
            // evidence, even if the physical recipe itself succeeded.
            MillReservations.taintUnexpectedProcess(level, pos);
            LOG.info("HEARTHBOUND_PROCESS_REJECT candidate-count={}; reserved job tainted",
                candidates.size());
            return;
        }
        var citizen=candidates.get(0);
        UUID job=MillExperimentTrace.jobId(citizen);
        if (!MillReservations.matches(level, pos, job, citizen.getUUID())) {
            MillReservations.taintUnexpectedProcess(level, pos);
            LOG.info("HEARTHBOUND_PROCESS_REJECT missing-or-conflicting-mill-reservation job={}; reserved machine invalidated", job);
            return;
        }
        long startTick = MillExperimentTrace.verifiedProcessingStartTick(citizen, pos, level.getGameTime());
        if (startTick < 0) {
            MillReservations.taint(level, pos, job, citizen.getUUID());
            LOG.warn("HEARTHBOUND_PROCESS_REJECT missing-observed-start job={}", job);
            return;
        }
        MillProcessReceipts ledger=get(level);
        if (ledger.receipts.containsKey(job)) {
            // A second real processing operation on a one-wheat experiment
            // invalidates the job instead of being treated as harmless replay.
            MillReservations.taint(level, pos, job, citizen.getUUID());
            LOG.info("HEARTHBOUND_PROCESS_REJECT extra-process tainted job={}", job);
            return;
        }
        ledger.receipts.put(job,new Receipt(job,citizen.getUUID(),pos.asLong(),startTick,level.getGameTime(),
            wheatBefore,wheatAfter,flourBefore,flourAfter));
        ledger.setDirty();
        boolean newlyRemembered = CitizenMillMemory.record(
            citizen, job, pos.asLong(), level.getGameTime());
        LOG.info("HEARTHBOUND_CITIZEN_MILL_EXPERIENCE citizen={} job={} recorded={} total={}",
            citizen.getUUID(), job, newlyRemembered, CitizenMillMemory.observedProcesses(citizen));
        LOG.info("HEARTHBOUND_PROCESS_RECEIPT job={} citizen={}", job, citizen.getUUID());
    }

    /**
     * Read-only raw callback record. Presence does not establish valid current
     * ownership or absence of later taint. Revalidate through exportVerified.
     */
    public static Receipt observedCallback(ServerLevel level, UUID job) {
        if (level == null || job == null) throw new IllegalArgumentException("missing job");
        return get(level).receipts.get(job);
    }

    /** Read-only raw receipt presence, including subsequently invalidated jobs. */
    public static boolean recorded(ServerLevel level, UUID job) {
        return get(level).receipts.containsKey(job);
    }

    /** Read-only proof that a direct Create processing receipt was recorded. */
    public static boolean hasReceipt(ServerLevel level, UUID job, UUID citizen, BlockPos machine) {
        Receipt receipt = get(level).receipts.get(job);
        return !MillReservations.isTainted(level, job)
            && receipt != null && receipt.citizen().equals(citizen)
            && receipt.pos() == machine.asLong()
            && receipt.startTick() >= 0 && receipt.startTick() < receipt.tick()
            && receipt.wheatBefore() - receipt.wheatAfter() == 1
            && receipt.flourAfter() > receipt.flourBefore();
    }

    /**
     * Export only a verified, untainted server receipt for a known job and citizen.
     * The caller must obtain worldIdentity from a durable per-save UUID, never a
     * random UUID or world seed regenerated during recovery.
     */
    public static dev.hearthbound.evidence.VerifiedMillAttribution.Claim exportVerified(
            ServerLevel level, UUID worldIdentity, UUID job, UUID citizen, BlockPos machine) {
        if (worldIdentity == null || !hasReceipt(level, job, citizen, machine)
                || !MillReservations.matches(level, machine, job, citizen))
            throw new IllegalArgumentException("unverified receipt or ownership");
        Receipt r = get(level).receipts.get(job);
        return dev.hearthbound.evidence.VerifiedMillAttribution.validate(
            new dev.hearthbound.evidence.VerifiedMillAttribution.Proof(
                worldIdentity, job, citizen, level.dimension().location().toString(),
                machine.asLong(), r.startTick(), r.tick(),
                r.wheatBefore(), r.wheatAfter(), r.flourBefore(), r.flourAfter(),
                true, MillReservations.isTainted(level, job)));
    }

    public static String inspect(ServerLevel level, UUID job) {
        Receipt receipt=get(level).receipts.get(job);
        if (MillReservations.isTainted(level, job))
            return "MILL_PROCESS INVALIDATED job="+job+" reason=TAINTED NO_RESEARCH_CREDIT";
        if (receipt==null) return "MILL_PROCESS NONE job="+job+" NO_RESEARCH_CREDIT";
        return "MILL_PROCESS VERIFIED_CALLBACK job="+job+" citizen="+receipt.citizen()
            +" wheatBefore="+receipt.wheatBefore()+" wheatAfter="+receipt.wheatAfter()
            +" flourBefore="+receipt.flourBefore()+" flourAfter="+receipt.flourAfter()
            +" startTick="+receipt.startTick()+" tick="+receipt.tick()+" NO_RESEARCH_CREDIT";
    }
}
