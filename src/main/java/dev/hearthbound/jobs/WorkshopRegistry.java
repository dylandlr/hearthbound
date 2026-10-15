package dev.hearthbound.jobs;

import java.util.HashMap;
import java.util.Map;
import java.util.UUID;
import dev.hearthbound.HearthboundMod;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.saveddata.SavedData;
import net.minecraftforge.event.entity.EntityLeaveLevelEvent;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Dimension-scoped ownership and durable job leases; never loads a holder's chunk. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class WorkshopRegistry extends SavedData {
    public static final UUID SERVER_OWNER = new UUID(0, 0);
    private final Map<Long, UUID> owners = new HashMap<>();
    private final StationReservations reservations = new StationReservations();
    private final Map<UUID, String> restoredJobs = new HashMap<>();

    /** Acceptance witness: a runtime reacquisition is not a saved-lease restoration. */
    public boolean wasRestored(UUID worker, String job) { return job.equals(restoredJobs.get(worker)); }

    public static WorkshopRegistry get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(WorkshopRegistry::load, WorkshopRegistry::new,
                "hearthbound_workshops");
    }
    public UUID owner(BlockPos mill) { return owners.get(mill.asLong()); }
    public boolean canUse(BlockPos mill, UUID manager, boolean operator) {
        UUID owner = owner(mill);
        return operator || (manager != null && (owner == null || owner.equals(manager)));
    }
    public UUID claim(BlockPos mill, UUID manager, boolean operator) {
        if (!canUse(mill, manager, operator)) throw new IllegalStateException("Workshop access denied");
        if (owner(mill) == null) {
            owners.put(mill.asLong(), manager == null ? SERVER_OWNER : manager);
            setDirty();
        }
        return owner(mill);
    }
    public StationReservations.Lease holder(BlockPos station) { return reservations.holder(station.asLong()); }
    public StationReservations.Lease lease(UUID worker) { return reservations.lease(worker); }
    public int waitingAt(BlockPos station, long now) { return reservations.waitingAt(station.asLong(), now); }
    public boolean isWaiting(UUID worker, BlockPos station, long now) {
        return reservations.isWaiting(worker, station.asLong(), now);
    }

    public boolean reserve(Villager worker, CompoundTag job) {
        reconcile(worker);
        boolean hadLease = lease(worker.getUUID()) != null;
        boolean acquired = reservations.acquire(worker.getUUID(), job.getString("JobId"),
                job.getLong("From"), job.getLong("To"), worker.level().getGameTime());
        if (acquired && !hadLease) setDirty();
        return acquired;
    }

    /** New assignments have not yet installed their job on the entity. */
    public boolean reserveNew(Villager worker, CompoundTag job) {
        reconcile(worker);
        boolean acquired = reservations.acquire(worker.getUUID(), job.getString("JobId"),
                job.getLong("From"), job.getLong("To"), worker.level().getGameTime());
        if (acquired) setDirty();
        return acquired;
    }

    public void release(Villager worker, String job) {
        if (reservations.release(worker.getUUID(), job)) setDirty();
    }
    public void cancelWaiting(Villager worker) { reservations.cancelWaiting(worker.getUUID()); }

    /** Reconcile only a loaded entity. Missing/unloaded holders retain their saved lease. */
    public void reconcile(Villager worker) {
        var lease = lease(worker.getUUID());
        if (lease == null) return;
        var data = worker.getPersistentData();
        var job = data.getCompound("HearthboundHaul");
        if (!worker.isAlive() || !worker.getTags().contains("hearthbound.sable")
                || !data.contains("HearthboundHaul", 10) || !lease.job().equals(job.getString("JobId"))
                || lease.from() != job.getLong("From") || lease.to() != job.getLong("To"))
            release(worker, lease.job());
    }

    @SubscribeEvent
    public static void tick(LivingEvent.LivingTickEvent event) {
        if (event.getEntity() instanceof Villager worker && worker.level() instanceof ServerLevel level
                && worker.tickCount % 20 == 0 && worker.getTags().contains("hearthbound.sable"))
            get(level).reconcile(worker);
    }

    @SubscribeEvent
    public static void leave(EntityLeaveLevelEvent event) {
        if (event.getEntity() instanceof Villager worker && event.getLevel() instanceof ServerLevel level
                && (worker.getTags().contains("hearthbound.sable") || worker.getPersistentData().contains("HearthboundHaul", 10))) {
            var registry = get(level);
            registry.cancelWaiting(worker);
            var reason = worker.getRemovalReason();
            // Unload, shutdown and dimension changes keep the lease.
            if (reason == net.minecraft.world.entity.Entity.RemovalReason.KILLED
                    || reason == net.minecraft.world.entity.Entity.RemovalReason.DISCARDED) {
                // A worker may have crossed dimensions while its original haul waited.
                // Clear its destroyed identity in each registry, without loading chunks.
                for (var savedLevel : level.getServer().getAllLevels()) {
                    var savedRegistry = get(savedLevel);
                    var lease = savedRegistry.lease(worker.getUUID());
                    if (lease != null) savedRegistry.release(worker, lease.job());
                }
            }
        }
    }

    public static int status(CommandSourceStack source, BlockPos mill) {
        var registry = get(source.getLevel());
        var lease = registry.holder(mill);
        source.sendSuccess(() -> Component.literal("Workshop owner=" + registry.owner(mill)
                + ", reservation=" + (lease == null ? "free" : lease.worker() + "/" + lease.job())), false);
        return 1;
    }

    public static int releaseOwnership(CommandSourceStack source, BlockPos mill) {
        var registry = get(source.getLevel());
        if (registry.holder(mill) != null) {
            source.sendFailure(Component.literal("Finish the reserved haul before releasing this workshop."));
            return 0;
        }
        if (registry.owners.remove(mill.asLong()) != null) registry.setDirty();
        source.sendSuccess(() -> Component.literal("Workshop ownership released. Save an order to claim it again."), false);
        return 1;
    }

    public static WorkshopRegistry load(CompoundTag tag) {
        var registry = new WorkshopRegistry();
        for (var entry : tag.getList("Owners", 10)) {
            var owner = (CompoundTag) entry;
            registry.owners.put(owner.getLong("Mill"), owner.getUUID("Owner"));
        }
        for (var entry : tag.getList("Leases", 10)) {
            var lease = (CompoundTag) entry;
            registry.reservations.restore(new StationReservations.Lease(lease.getUUID("Worker"),
                    lease.getString("Job"), lease.getLong("From"), lease.getLong("To")));
            registry.restoredJobs.put(lease.getUUID("Worker"), lease.getString("Job"));
        }
        return registry;
    }

    @Override public CompoundTag save(CompoundTag tag) {
        var ownersTag = new ListTag();
        owners.forEach((mill, owner) -> {
            var entry = new CompoundTag(); entry.putLong("Mill", mill); entry.putUUID("Owner", owner);
            ownersTag.add(entry);
        });
        var leasesTag = new ListTag();
        for (var lease : reservations.leases()) {
            var entry = new CompoundTag();
            entry.putUUID("Worker", lease.worker()); entry.putString("Job", lease.job());
            entry.putLong("From", lease.from()); entry.putLong("To", lease.to());
            leasesTag.add(entry);
        }
        tag.put("Owners", ownersTag); tag.put("Leases", leasesTag);
        return tag;
    }
}
