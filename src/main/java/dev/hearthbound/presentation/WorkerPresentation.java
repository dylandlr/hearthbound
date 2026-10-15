package dev.hearthbound.presentation;

import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraft.core.registries.BuiltInRegistries;

/** Derives a display from the same persisted job and actual stockpile used by production. */
public final class WorkerPresentation {
    private WorkerPresentation() {}

    public static int status(net.minecraft.commands.CommandSourceStack source) {
        Villager worker = dev.hearthbound.jobs.SableSelection.nearest(source, v -> true);
        if (worker == null) {
            source.sendFailure(net.minecraft.network.chat.Component.literal("No colony worker nearby."));
            return 0;
        }
        var view = inspect(worker);
        source.sendSuccess(() -> net.minecraft.network.chat.Component.literal("HB_WORKER_VIEW activity="
                + view.activity() + " cargo=" + view.cargo() + " item=" + view.item()
                + " order=" + view.hasOrder() + " flour=" + view.stockedFlour()
                + " target=" + view.targetFlour()), false);
        return 1;
    }

    public static WorkerView inspect(Villager worker) {
        var data = worker.getPersistentData();
        boolean visible = worker.getTags().contains("hearthbound.sable");
        var haul = data.getCompound("HearthboundHaul");
        boolean hasHaul = data.contains("HearthboundHaul", 10);
        boolean hasOrder = data.contains("HearthboundMillOrder", 10);
        var order = data.getCompound("HearthboundMillOrder");
        int stocked = -1;
        if (hasOrder && worker.level() instanceof ServerLevel level) {
            BlockPos storage = BlockPos.of(order.getLong("Flour"));
            if (level.hasChunkAt(storage) && level.getBlockEntity(storage) instanceof BarrelBlockEntity barrel) {
                stocked = 0;
                for (int slot = 0; slot < barrel.getContainerSize(); slot++) {
                    var stack = barrel.getItem(slot);
                    if (BuiltInRegistries.ITEM.getKey(stack.getItem()).toString().equals("create:wheat_flour"))
                        stocked += stack.getCount();
                }
            }
        }
        return new WorkerView(visible, hasHaul ? haul.getString("Item") : "minecraft:air",
                Math.max(0, Math.min(64, haul.getInt("Cargo"))), activity(data, haul, order, hasHaul, hasOrder),
                hasOrder, stocked, Math.max(0, Math.min(4096, order.getInt("TargetFlour"))));
    }

    private static String activity(CompoundTag data, CompoundTag haul, CompoundTag order,
            boolean hasHaul, boolean hasOrder) {
        if (hasHaul) {
            if (haul.getBoolean("Paused")) return "paused";
            String result = haul.getString("Result");
            if (result.startsWith("OUTPUT_FULL")) return "output_full";
            if (result.startsWith("MISSING_")) return "missing_station";
            if (result.equals("WAITING_FOR_CHUNK")) return "waiting_for_chunks";
            if (result.equals("NO_ACCESSIBLE_STATION")) return "no_access";
            if (result.equals("NO_WHEAT")) return "waiting_for_supplies";
            if (result.equals("PICKING_UP")) return "picking_up";
            if (result.equals("PUTTING_DOWN")) return "putting_down";
            return haul.getString("Phase").equals("PICKUP") ? "collecting" : "delivering";
        }
        if (hasOrder) {
            switch (order.getString("WaitState")) {
                case "RETURNING": return "returning_to_workshop";
                case "BLOCKED": return "wait_blocked";
                case "UNLOADED": return "waiting_for_chunks";
            }
            return switch (order.getString("State")) {
                case "MILLING" -> "milling";
                case "TARGET_REACHED" -> "target_reached";
                case "WAITING_FOR_WHEAT" -> "waiting_for_supplies";
                case "WAITING_FOR_CHUNKS" -> "waiting_for_chunks";
                case "MISSING_STATION" -> "missing_station";
                default -> "waiting";
            };
        }
        return data.getBoolean("HearthboundTravelActive") ? "travelling" : "idle";
    }
}
