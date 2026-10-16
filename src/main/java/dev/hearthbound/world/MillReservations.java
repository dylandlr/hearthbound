package dev.hearthbound.world;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/**
 * Persistent Hearthbound-owned mill reservations. Never auto-expires:
 * interruption or restart requires operator examination.
 *
 * WARNING: This prevents competing Hearthbound jobs, not Create conveyors,
 * vanilla hoppers, players or other mods. Do not award learning credit yet.
 */
public final class MillReservations extends SavedData {
    private static final String KEY = "hearthbound_mill_reservations_v1";
    private static final ResourceLocation MILL = new ResourceLocation("create", "millstone");
    private final Map<Long, Reservation> leases = new HashMap<>();
    // Released-job tombstones remain saved to support replay rejection and audit.
    private final Map<UUID, Long> released = new HashMap<>();

    public record Reservation(UUID job, UUID citizen, long position) {}

    private static MillReservations get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(MillReservations::load, MillReservations::new, KEY);
    }

    private static MillReservations load(CompoundTag root) {
        MillReservations data = new MillReservations();
        ListTag list = root.getList("reservations", Tag.TAG_COMPOUND);
        for (int i = 0; i < list.size(); i++) {
            CompoundTag entry = list.getCompound(i);
            if (!entry.hasUUID("job") || !entry.hasUUID("citizen"))
                throw new IllegalStateException("Corrupt mill reservation");
            Reservation lease = new Reservation(entry.getUUID("job"),
                entry.getUUID("citizen"), entry.getLong("position"));
            if (data.leases.putIfAbsent(lease.position(), lease) != null)
                throw new IllegalStateException("Duplicate mill reservation position");
        }
        ListTag history = root.getList("released", Tag.TAG_COMPOUND);
        for (int i = 0; i < history.size(); i++) {
            CompoundTag entry = history.getCompound(i);
            if (!entry.hasUUID("job")) throw new IllegalStateException("Corrupt release history");
            if (data.released.putIfAbsent(entry.getUUID("job"), entry.getLong("position")) != null)
                throw new IllegalStateException("Duplicate release tombstone");
        }
        return data;
    }

    @Override
    public CompoundTag save(CompoundTag root) {
        ListTag list = new ListTag();
        leases.values().stream().sorted((a,b)->Long.compare(a.position(), b.position()))
            .forEach(lease -> {
                CompoundTag tag = new CompoundTag();
                tag.putUUID("job", lease.job());
                tag.putUUID("citizen", lease.citizen());
                tag.putLong("position", lease.position());
                list.add(tag);
            });
        root.put("reservations", list);
        ListTag history = new ListTag();
        released.entrySet().stream().sorted(Map.Entry.comparingByKey()).forEach(entry -> {
            CompoundTag tag = new CompoundTag();
            tag.putUUID("job", entry.getKey());
            tag.putLong("position", entry.getValue());
            history.add(tag);
        });
        root.put("released", history);
        return root;
    }

    public static boolean isMill(ServerLevel level, BlockPos pos) {
        return level.hasChunkAt(pos) &&
            MILL.equals(BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock()));
    }

    /** Non-mill destinations don't require an exclusive reservation. */
    public static boolean acquireIfMill(ServerLevel level, BlockPos pos, UUID job, UUID citizen) {
        if (!isMill(level, pos)) return true;
        MillReservations data = get(level);
        if (data.released.containsKey(job)) return false;
        Reservation prior = data.leases.get(pos.asLong());
        if (prior != null)
            return prior.job().equals(job) && prior.citizen().equals(citizen);
        // A fresh experimental lease requires an empty physical machine.
        // Otherwise pre-existing inputs or outputs make result attribution unsafe.
        if (!(level.getBlockEntity(pos) instanceof
                com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity machine))
            return false;
        for (int i = 0; i < machine.inputInv.getSlots(); i++)
            if (!machine.inputInv.getStackInSlot(i).isEmpty()) return false;
        for (int i = 0; i < machine.outputInv.getSlots(); i++)
            if (!machine.outputInv.getStackInSlot(i).isEmpty()) return false;
        data.leases.put(pos.asLong(), new Reservation(job, citizen, pos.asLong()));
        data.setDirty();
        return true;
    }

    /**
     * Release only before physical pickup. Completed mill experiments retain
     * their reservation until a separate audited reconciliation path exists.
     */
    public static boolean releaseUnpicked(ServerLevel level, BlockPos pos, UUID job, UUID citizen) {
        if (!isMill(level, pos)) return true;
        MillReservations data = get(level);
        Reservation existing = data.leases.get(pos.asLong());
        if (existing == null || !existing.job().equals(job) ||
                !existing.citizen().equals(citizen)) return false;
        data.leases.remove(pos.asLong());
        data.setDirty();
        return true;
    }

    /**
     * Operator-reviewed release. This is not a proof of exclusive item origin:
     * it only closes a reservation after the demonstrated Create operation.
     * No automatic learning or item mutation occurs.
     */
    public static void releaseCompleted(ServerLevel level, BlockPos pos, UUID job,
                                        net.minecraft.world.entity.npc.Villager citizen) {
        MillReservations journal = get(level);
        Reservation held = journal.leases.get(pos.asLong());
        if (held == null || !held.job().equals(job) || !held.citizen().equals(citizen.getUUID()))
            throw new IllegalStateException("Mill reservation does not match job and citizen");
        if (!isMill(level, pos))
            throw new IllegalStateException("Loaded millstone required for release");
        if (!SableHauling.completedJob(citizen, job, pos))
            throw new IllegalStateException("Job is not a cargo-free completed delivery");
        if (!MillProcessReceipts.hasReceipt(level, job, citizen.getUUID(), pos))
            throw new IllegalStateException("Direct Create processing receipt missing");
        if (!(level.getBlockEntity(pos) instanceof
                com.simibubi.create.content.kinetics.millstone.MillstoneBlockEntity machine))
            throw new IllegalStateException("Create millstone inventory unavailable");
        for (int i = 0; i < machine.inputInv.getSlots(); i++)
            if (!machine.inputInv.getStackInSlot(i).isEmpty())
                throw new IllegalStateException("Millstone input must be empty");
        for (int i = 0; i < machine.outputInv.getSlots(); i++)
            if (!machine.outputInv.getStackInSlot(i).isEmpty())
                throw new IllegalStateException("Collect all millstone output before release");
        if (journal.released.containsKey(job))
            throw new IllegalStateException("Job already released");
        journal.leases.remove(pos.asLong());
        journal.released.put(job, pos.asLong());
        journal.setDirty();
    }

    public static boolean matches(ServerLevel level, BlockPos pos, UUID job, UUID citizen) {
        Reservation lease = get(level).leases.get(pos.asLong());
        return lease != null && lease.job().equals(job) && lease.citizen().equals(citizen);
    }

    public static String audit(ServerLevel level, BlockPos pos) {
        Reservation lease = get(level).leases.get(pos.asLong());
        if (lease == null) return "MILL_RESERVATION NONE pos=" + pos + " NO_RESEARCH_CREDIT";
        return "MILL_RESERVATION HELD pos=" + pos + " job=" + lease.job()
            + " citizen=" + lease.citizen() + " NO_RESEARCH_CREDIT";
    }
}
