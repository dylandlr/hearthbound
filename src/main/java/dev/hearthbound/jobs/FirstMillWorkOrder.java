package dev.hearthbound.jobs;

import dev.hearthbound.HearthboundMod;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** First playable, opt-in, persistent job scheduler. Villager remains server-authoritative. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class FirstMillWorkOrder {
    private static final String ROOT = "HearthboundMillOrder";
    private FirstMillWorkOrder() {}

    public static int start(CommandSourceStack source, BlockPos wheat, BlockPos mill, BlockPos flour) {
        ServerLevel level = source.getLevel();
        if (wheat.equals(mill) || wheat.equals(flour) || mill.equals(flour)
                || !level.hasChunkAt(wheat) || !level.hasChunkAt(mill) || !level.hasChunkAt(flour)
                || !(level.getBlockEntity(wheat) instanceof BarrelBlockEntity)
                || !(level.getBlockEntity(flour) instanceof BarrelBlockEntity)
                || !isMillstone(level, mill)) {
            source.sendFailure(Component.literal("Work order needs two loaded barrels and a Create millstone."));
            return 0;
        }
        Villager worker = SableSelection.nearest(source, SableSelection::idle);
        if (worker == null) {
            source.sendFailure(Component.literal("No unassigned Sable within 32 blocks."));
            return 0;
        }
        String error = configure(worker, wheat, mill, flour, null, 0);
        if (!error.isEmpty()) { source.sendFailure(Component.literal(error)); return 0; }
        source.sendSuccess(() -> Component.literal("First Mill work order enabled for Sable."), false);
        return 1;
    }

    public static long revision(Villager worker) {
        return worker.getPersistentData().getLong("HearthboundOrderRevision");
    }

    public static void advanceRevision(Villager worker) {
        worker.getPersistentData().putLong("HearthboundOrderRevision", revision(worker) + 1);
    }

    private static void changed(Villager worker) {
        advanceRevision(worker);
        worker.getPersistentData().put("HearthboundWorkshopSetup", worker.getPersistentData().getCompound(ROOT).copy());
    }

    /** Shared command/UI mutation. Validate everything before touching the order or cargo. */
    public static String configure(Villager worker, BlockPos wheat, BlockPos mill, BlockPos flour,
            BlockPos wait, int target) {
        var data = worker.getPersistentData();
        return configureFor(worker, wheat, mill, flour, wait, target,
                data.hasUUID("HearthboundSupervisor") ? data.getUUID("HearthboundSupervisor") : null, true);
    }

    /** UI callers supply the actual sender; operator commands use the trusted wrapper. */
    public static String configureFor(Villager worker, BlockPos wheat, BlockPos mill, BlockPos flour,
            BlockPos wait, int target, java.util.UUID manager, boolean operator) {
        if (!(worker.level() instanceof ServerLevel level)) return "Workshop is unavailable.";
        if (target < 0 || target > 4096) return "Use a flour target from 0 to 4096.";
        if (wheat == null || mill == null || flour == null || wheat.equals(mill) || wheat.equals(flour)
                || mill.equals(flour) || !level.hasChunkAt(wheat) || !level.hasChunkAt(mill) || !level.hasChunkAt(flour)
                || !(level.getBlockEntity(wheat) instanceof BarrelBlockEntity)
                || !(level.getBlockEntity(flour) instanceof BarrelBlockEntity)
                || !isMillstone(level, mill))
            return "Choose two distinct loaded barrels and a Create millstone.";
        var data = worker.getPersistentData();
        boolean existing = data.contains(ROOT, 10);
        if (!existing && !SableSelection.idle(worker)) return "Wait for the current job to finish.";
        var order = existing ? data.getCompound(ROOT).copy() : new CompoundTag();
        if (existing && (order.getLong("Wheat") != wheat.asLong() || order.getLong("Mill") != mill.asLong()
                || order.getLong("Flour") != flour.asLong())) return "Stop the order before changing its stations.";
        order.putLong("Wheat", wheat.asLong()); order.putLong("Mill", mill.asLong()); order.putLong("Flour", flour.asLong());
        order.putInt("TargetFlour", target);
        if (wait != null) {
            if (!WorkshopWaiting.valid(level, wait, order)) return "Choose clear supported floor away from the stations.";
            order.putLong("Wait", wait.asLong());
        } else if (!existing) WorkshopWaiting.setDefault(level, worker, order);
        var registry = WorkshopRegistry.get(level);
        if (!registry.canUse(mill, manager, operator)) return "This mill belongs to another supervisor.";
        order.putUUID("WorkshopOwner", registry.claim(mill, manager, operator));
        registry.cancelWaiting(worker);
        order.putBoolean("Enabled", true);
        if (!existing) order.putString("State", "WAITING");
        order.remove("WaitState"); order.remove("WaitRetryAfter");
        data.put(ROOT, order);
        WorkshopWaiting.forget(worker);
        if (!data.contains("HearthboundHaul", 10)) worker.getNavigation().stop();
        changed(worker);
        return "";
    }

    public static int waitingPoint(CommandSourceStack source, BlockPos feet) {
        Villager worker = SableSelection.nearest(source, v -> v.getPersistentData().contains(ROOT, 10));
        if (worker == null) { source.sendFailure(Component.literal("No First Mill work order nearby.")); return 0; }
        var order = worker.getPersistentData().getCompound(ROOT);
        if (!WorkshopWaiting.valid(source.getLevel(), feet, order)) {
            source.sendFailure(Component.literal("Choose clear floor within 32 blocks of the mill, away from station blocks.")); return 0;
        }
        order.putLong("Wait", feet.asLong()); order.remove("WaitState"); order.remove("WaitRetryAfter");
        WorkshopWaiting.forget(worker);
        if (!worker.getPersistentData().contains("HearthboundHaul", 10)) worker.getNavigation().stop();
        changed(worker);
        source.sendSuccess(() -> Component.literal("First Mill waiting spot set to " + feet.toShortString()), false);
        return 1;
    }

    public static int target(CommandSourceStack source, int amount) {
        if (amount < 1 || amount > 4096) { source.sendFailure(Component.literal("Target must be between 1 and 4096 flour.")); return 0; }
        Villager worker = SableSelection.nearest(source, v -> v.getPersistentData().contains(ROOT, 10));
        if (worker == null) { source.sendFailure(Component.literal("No First Mill work order nearby.")); return 0; }
        worker.getPersistentData().getCompound(ROOT).putInt("TargetFlour", amount);
        changed(worker);
        source.sendSuccess(() -> Component.literal("First Mill flour target set to " + amount), false);
        return 1;
    }

    public static void stopWorker(Villager worker) {
        // Keep a reusable setup, and never erase the active haul or its cargo.
        changed(worker);
        if (!worker.getPersistentData().contains("HearthboundHaul", 10)) worker.getNavigation().stop();
        WorkshopWaiting.forget(worker);
        worker.getPersistentData().remove(ROOT);
        if (worker.level() instanceof ServerLevel level) WorkshopRegistry.get(level).cancelWaiting(worker);
    }

    public static int stop(CommandSourceStack source) {
        Villager worker = SableSelection.nearest(source, v -> v.getPersistentData().contains(ROOT, 10));
        if (worker == null) { source.sendFailure(Component.literal("No First Mill work order nearby.")); return 0; }
        stopWorker(worker);
        source.sendSuccess(() -> Component.literal("First Mill scheduling stopped; existing haul retained."), false);
        return 1;
    }

    public static int status(CommandSourceStack source) {
        Villager worker = SableSelection.nearest(source,
                v -> v.getPersistentData().contains(ROOT, 10));
        if (worker == null) {
            source.sendFailure(Component.literal("No First Mill work order nearby."));
            return 0;
        }
        CompoundTag order = worker.getPersistentData().getCompound(ROOT);
        String state = order.getString("State");
        String hauling = worker.getPersistentData().contains("HearthboundHaul", 10)
                ? worker.getPersistentData().getCompound("HearthboundHaul").getString("Phase") : "IDLE";
        source.sendSuccess(() -> Component.literal("First Mill: state=" + state
                + ", worker=" + worker.getUUID() + ", hauling=" + hauling
                + ", target=" + (order.getInt("TargetFlour") > 0
                        ? order.getInt("TargetFlour") : "unlimited")
                + ", wait=" + (order.contains("Wait") ? BlockPos.of(order.getLong("Wait")).toShortString() : "unavailable")
                + ", waitState=" + order.getString("WaitState")
                + ", wheat=" + BlockPos.of(order.getLong("Wheat"))
                + ", mill=" + BlockPos.of(order.getLong("Mill"))
                + ", flour=" + BlockPos.of(order.getLong("Flour"))), false);
        return 1;
    }

    @SubscribeEvent
    public static void tick(LivingEvent.LivingTickEvent event) {
        Entity entity = event.getEntity();
        if (!(entity instanceof Villager villager) || entity.level().isClientSide()
                || villager.tickCount % 40 != 0
                || !villager.getPersistentData().contains(ROOT, 10)
                || !(entity.level() instanceof ServerLevel level)) return;
        CompoundTag data = villager.getPersistentData();
        CompoundTag order = data.getCompound(ROOT);
        if (!order.getBoolean("Enabled") || data.contains("HearthboundHaul", 10)) return;
        BlockPos wheat = BlockPos.of(order.getLong("Wheat"));
        BlockPos mill = BlockPos.of(order.getLong("Mill"));
        BlockPos flour = BlockPos.of(order.getLong("Flour"));
        if (!level.hasChunkAt(wheat) || !level.hasChunkAt(mill) || !level.hasChunkAt(flour)) {
            order.putString("State", "WAITING_FOR_CHUNKS");
            return;
        }
        if (!(level.getBlockEntity(wheat) instanceof BarrelBlockEntity supply)
                || !(level.getBlockEntity(flour) instanceof BarrelBlockEntity)
                || !isMillstone(level, mill)) {
            order.putString("State", "MISSING_STATION");
            return;
        }
        var registry = WorkshopRegistry.get(level);
        // Existing worlds adopt their old supervisor (or server ownership) once.
        if (!order.hasUUID("WorkshopOwner")) {
            var manager = data.hasUUID("HearthboundSupervisor") ? data.getUUID("HearthboundSupervisor") : WorkshopRegistry.SERVER_OWNER;
            if (!registry.canUse(mill, manager, false)) {
                order.putString("State", "WORKSHOP_ACCESS_DENIED"); registry.cancelWaiting(villager); return;
            }
            order.putUUID("WorkshopOwner", registry.claim(mill, manager, false));
        }
        if (!order.getUUID("WorkshopOwner").equals(registry.owner(mill))) {
            order.putString("State", "WORKSHOP_ACCESS_DENIED"); registry.cancelWaiting(villager); return;
        }
        int targetFlour = order.getInt("TargetFlour");
        if (targetFlour > 0 && level.getBlockEntity(flour) instanceof BarrelBlockEntity store) {
            var flourItem = BuiltInRegistries.ITEM.get(new ResourceLocation("create", "wheat_flour"));
            int stocked = 0;
            for (int i = 0; i < store.getContainerSize(); i++)
                if (store.getItem(i).is(flourItem)) stocked += store.getItem(i).getCount();
            if (stocked >= targetFlour) {
                registry.cancelWaiting(villager);
                order.putString("State", "TARGET_REACHED");
                return;
            }
        }
        // Prioritize finished goods. Otherwise supply up to four wheat.
        if (hasFlourOutput(level, mill)) {
            if (BarrelHaulController.assignFlourCitizen(villager, mill, flour, 1)) {
                WorkshopWaiting.beginWork(villager, order);
                order.putString("State", "COLLECTING_FLOUR");
            } else order.putString("State", "WAITING_FOR_STATION");
            return;
        }
        // Do not queue fresh deliveries while wheat is still in the millstone.
        // This avoids a citizen collecting excess wheat and stalling with cargo.
        if (hasMillInput(level, mill)) {
            registry.cancelWaiting(villager);
            order.putString("State", "MILLING");
            return;
        }
        int wheatCount = 0;
        for (int i = 0; i < supply.getContainerSize(); i++)
            if (supply.getItem(i).is(Items.WHEAT)) wheatCount += supply.getItem(i).getCount();
        if (wheatCount > 0) {
            if (BarrelHaulController.assignCitizen(villager, wheat, mill, Math.min(4, wheatCount))) {
                WorkshopWaiting.beginWork(villager, order);
                order.putString("State", "SUPPLYING_WHEAT");
            } else order.putString("State", "WAITING_FOR_STATION");
        } else {
            registry.cancelWaiting(villager);
            order.putString("State", "WAITING_FOR_WHEAT");
        }
    }

    private static boolean isMillstone(ServerLevel level, BlockPos pos) {
        return BuiltInRegistries.BLOCK.getKey(level.getBlockState(pos).getBlock())
                .equals(new ResourceLocation("create", "millstone"));
    }

    private static boolean hasMillInput(ServerLevel level, BlockPos pos) {
        var entity = level.getBlockEntity(pos);
        if (entity == null) return false;
        var handler = entity.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER,
                net.minecraft.core.Direction.UP).orElse(null);
        if (handler == null) return false;
        for (int i = 0; i < handler.getSlots(); i++)
            if (handler.getStackInSlot(i).is(Items.WHEAT)) return true;
        return false;
    }

    private static boolean hasFlourOutput(ServerLevel level, BlockPos pos) {
        var entity = level.getBlockEntity(pos);
        if (entity == null) return false;
        var handler = entity.getCapability(net.minecraftforge.common.capabilities.ForgeCapabilities.ITEM_HANDLER,
                net.minecraft.core.Direction.EAST).orElse(null);
        if (handler == null) return false;
        var flour = BuiltInRegistries.ITEM.get(new ResourceLocation("create", "wheat_flour"));
        for (int i = 0; i < handler.getSlots(); i++)
            if (handler.getStackInSlot(i).is(flour)) return true;
        return false;
    }
}
