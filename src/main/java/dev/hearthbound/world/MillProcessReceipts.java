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

    public record Receipt(UUID job, UUID citizen, long pos, long tick, int wheatBefore,
                          int wheatAfter, int flourBefore, int flourAfter) {}

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
            t.putInt("wheatBefore",receipt.wheatBefore());
            t.putInt("wheatAfter",receipt.wheatAfter());
            t.putInt("flourBefore",receipt.flourBefore());
            t.putInt("flourAfter",receipt.flourAfter());
            list.add(t);
        });
        tag.put("receipts",list);
        return tag;
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
            LOG.info("HEARTHBOUND_PROCESS_REJECT candidate-count={}", candidates.size());
            return;
        }
        var citizen=candidates.get(0);
        UUID job=MillExperimentTrace.jobId(citizen);
        if (!MillReservations.matches(level, pos, job, citizen.getUUID())) {
            LOG.info("HEARTHBOUND_PROCESS_REJECT missing-or-conflicting-mill-reservation job={}", job);
            return;
        }
        MillProcessReceipts ledger=get(level);
        if (ledger.receipts.containsKey(job)) {
            LOG.info("HEARTHBOUND_PROCESS_REPLAY job={}", job);
            return;
        }
        ledger.receipts.put(job,new Receipt(job,citizen.getUUID(),pos.asLong(),level.getGameTime(),
            wheatBefore,wheatAfter,flourBefore,flourAfter));
        ledger.setDirty();
        LOG.info("HEARTHBOUND_PROCESS_RECEIPT job={} citizen={}", job, citizen.getUUID());
    }

    /** Read-only proof that a direct Create processing receipt was recorded. */
    public static boolean hasReceipt(ServerLevel level, UUID job, UUID citizen, BlockPos machine) {
        Receipt receipt = get(level).receipts.get(job);
        return !MillReservations.isTainted(level, job)
            && receipt != null && receipt.citizen().equals(citizen)
            && receipt.pos() == machine.asLong()
            && receipt.wheatBefore() - receipt.wheatAfter() == 1
            && receipt.flourAfter() > receipt.flourBefore();
    }

    public static String inspect(ServerLevel level, UUID job) {
        Receipt receipt=get(level).receipts.get(job);
        if (MillReservations.isTainted(level, job))
            return "MILL_PROCESS INVALIDATED job="+job+" reason=TAINTED NO_RESEARCH_CREDIT";
        if (receipt==null) return "MILL_PROCESS NONE job="+job+" NO_RESEARCH_CREDIT";
        return "MILL_PROCESS VERIFIED_CALLBACK job="+job+" citizen="+receipt.citizen()
            +" wheatBefore="+receipt.wheatBefore()+" wheatAfter="+receipt.wheatAfter()
            +" flourBefore="+receipt.flourBefore()+" flourAfter="+receipt.flourAfter()
            +" tick="+receipt.tick()+" NO_RESEARCH_CREDIT";
    }
}
