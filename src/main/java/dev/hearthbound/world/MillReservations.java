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
        Reservation prior = data.leases.get(pos.asLong());
        if (prior != null)
            return prior.job().equals(job) && prior.citizen().equals(citizen);
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
