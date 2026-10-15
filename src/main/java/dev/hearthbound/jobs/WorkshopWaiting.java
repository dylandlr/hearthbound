package dev.hearthbound.jobs;

import dev.hearthbound.HearthboundMod;
import java.util.Map;
import java.util.WeakHashMap;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** An order's safe resting position. Waiting never owns cargo or forces chunks. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class WorkshopWaiting {
    private static final Map<Villager, TravelProgress> TRAVEL = new WeakHashMap<>();
    private static final Map<Villager, List<BlockPos>> DETOURS = new WeakHashMap<>();
    private WorkshopWaiting() {}

    private static BlockPos[] stations(CompoundTag order) {
        return new BlockPos[] {BlockPos.of(order.getLong("Wheat")), BlockPos.of(order.getLong("Mill")),
                BlockPos.of(order.getLong("Flour"))};
    }

    public static boolean valid(ServerLevel level, BlockPos feet, CompoundTag order) {
        if (!StationApproach.standable(level, feet)
                || feet.distSqr(BlockPos.of(order.getLong("Mill"))) > 32 * 32) return false;
        for (BlockPos station : stations(order))
            if (Math.abs(feet.getX() - station.getX()) + Math.abs(feet.getZ() - station.getZ()) < 2)
                return false;
        return true;
    }

    public static void setDefault(ServerLevel level, Villager worker, CompoundTag order) {
        if (valid(level, worker.blockPosition(), order)) {
            order.putLong("Wait", worker.blockPosition().asLong());
            return;
        }
        BlockPos mill = BlockPos.of(order.getLong("Mill"));
        for (int radius = 2; radius <= 4; radius++)
            for (int dx = -radius; dx <= radius; dx++)
                for (int dz = -radius; dz <= radius; dz++) {
                    if (Math.abs(dx) + Math.abs(dz) != radius) continue;
                    for (int dy = -1; dy <= 1; dy++) {
                        BlockPos feet = mill.offset(dx, dy, dz);
                        if (valid(level, feet, order)) {
                            order.putLong("Wait", feet.asLong());
                            return;
                        }
                    }
                }
        order.putString("WaitState", "BLOCKED");
    }

    public static void forget(Villager worker) { TRAVEL.remove(worker); DETOURS.remove(worker); }

    public static void beginWork(Villager worker, CompoundTag order) {
        forget(worker);
        worker.getNavigation().stop();
        order.remove("WaitState");
        order.remove("WaitRetryAfter");
    }

    @SubscribeEvent(priority = EventPriority.LOW)
    public static void tick(LivingEvent.LivingTickEvent event) {
        if (!(event.getEntity() instanceof Villager worker) || !(worker.level() instanceof ServerLevel level)
                || worker.tickCount % 20 != 0 || !worker.getTags().contains("hearthbound.sable")) return;
        var data = worker.getPersistentData();
        if (!data.contains("HearthboundMillOrder", 10)) { forget(worker); return; }
        var order = data.getCompound("HearthboundMillOrder");
        if (data.contains("HearthboundHaul", 10) || !order.getBoolean("Enabled")) {
            forget(worker);
            order.remove("WaitState");
            return;
        }
        if (!order.contains("Wait")) setDefault(level, worker, order);
        if (!order.contains("Wait")) { worker.getNavigation().stop(); return; }
        BlockPos feet = BlockPos.of(order.getLong("Wait"));
        if (!level.hasChunkAt(feet)) {
            worker.getNavigation().stop();
            order.putString("WaitState", "UNLOADED");
            forget(worker);
            return;
        }
        long now = level.getGameTime();
        if (now < order.getLong("WaitRetryAfter")) return;
        if (!valid(level, feet, order)) { blocked(worker, order, now); return; }
        if (atFeet(worker, feet)) {
            worker.getNavigation().stop();
            order.putString("WaitState", "AT_WAIT");
            BlockPos mill = BlockPos.of(order.getLong("Mill"));
            worker.getLookControl().setLookAt(mill.getX() + .5, mill.getY() + .5, mill.getZ() + .5);
            forget(worker);
            return;
        }
        double distance = Math.max(5.0, worker.distanceToSqr(feet.getX() + .5, feet.getY(), feet.getZ() + .5));
        var watch = TRAVEL.computeIfAbsent(worker, ignored -> new TravelProgress(now, distance));
        var outcome = watch.sample(now, distance);
        if (outcome == TravelProgress.Outcome.STALLED || outcome == TravelProgress.Outcome.TIMED_OUT
                || !moveToWaiting(level, worker, feet, stations(order))) {
            blocked(worker, order, now);
            return;
        }
        order.putString("WaitState", "RETURNING");
    }

    private static boolean atFeet(Villager worker, BlockPos feet) {
        return worker.blockPosition().equals(feet)
                && worker.distanceToSqr(feet.getX() + .5, feet.getY(), feet.getZ() + .5) <= .64;
    }

    /** Vanilla A* may prefer climbing a barrel over an equally reachable floor route.
     * Keep that route rejected, then try supported lanes outside the station bounds.
     * Every leg still uses a complete, checked vanilla navigation path.
     */
    private static boolean moveToWaiting(ServerLevel level, Villager worker, BlockPos feet, BlockPos[] stations) {
        var route = DETOURS.get(worker);
        if (route != null) {
            while (!route.isEmpty() && atFeet(worker, route.get(0))) route.remove(0);
            if (!route.isEmpty()) return StationApproach.moveToFeet(level, worker, route.get(0), stations);
            DETOURS.remove(worker);
        }
        if (StationApproach.moveToFeet(level, worker, feet, stations)) return true;
        int minX = feet.getX(), maxX = feet.getX(), minZ = feet.getZ(), maxZ = feet.getZ();
        for (BlockPos station : stations) {
            minX = Math.min(minX, station.getX()); maxX = Math.max(maxX, station.getX());
            minZ = Math.min(minZ, station.getZ()); maxZ = Math.max(maxZ, station.getZ());
        }
        BlockPos start = worker.blockPosition();
        var candidates = List.of(
                List.of(new BlockPos(start.getX(), feet.getY(), minZ - 2), new BlockPos(feet.getX(), feet.getY(), minZ - 2), feet),
                List.of(new BlockPos(start.getX(), feet.getY(), maxZ + 2), new BlockPos(feet.getX(), feet.getY(), maxZ + 2), feet),
                List.of(new BlockPos(minX - 2, feet.getY(), start.getZ()), new BlockPos(minX - 2, feet.getY(), feet.getZ()), feet),
                List.of(new BlockPos(maxX + 2, feet.getY(), start.getZ()), new BlockPos(maxX + 2, feet.getY(), feet.getZ()), feet));
        for (var candidate : candidates) {
            if (candidate.stream().anyMatch(point -> !StationApproach.standable(level, point))) continue;
            route = new ArrayList<>(candidate);
            while (!route.isEmpty() && atFeet(worker, route.get(0))) route.remove(0);
            if (!route.isEmpty() && StationApproach.moveToFeet(level, worker, route.get(0), stations)) {
                DETOURS.put(worker, route);
                return true;
            }
        }
        return false;
    }

    private static void blocked(Villager worker, CompoundTag order, long now) {
        worker.getNavigation().stop();
        order.putString("WaitState", "BLOCKED");
        order.putLong("WaitRetryAfter", now + 40);
        forget(worker);
    }
}
