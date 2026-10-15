package dev.hearthbound.jobs;

import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.entity.BarrelBlockEntity;
import net.minecraft.world.phys.AABB;
import java.util.List;

/** Detects a saved in-flight haul after a complete Forge server restart.
 * The test stage is set up by HaulE2EProbe and uses entity/world NBT, never static state.
 */
@net.minecraftforge.fml.common.Mod.EventBusSubscriber(modid = dev.hearthbound.HearthboundMod.MOD_ID)
public final class HaulRestartProbe {
    private HaulRestartProbe() {}

    public static int check(CommandSourceStack source) {
        ServerLevel level = source.getLevel();
        BlockPos spawn = level.getSharedSpawnPos();
        int top = level.getHeight(net.minecraft.world.level.levelgen.Heightmap.Types.MOTION_BLOCKING_NO_LEAVES,
                spawn.getX(), spawn.getZ());
        // The elevated CI platform may be above world terrain; locate test villager by tag.
        List<Villager> matches = level.getEntitiesOfClass(Villager.class,
                new AABB(spawn.getX() - 32, level.getMinBuildHeight(), spawn.getZ() - 32,
                        spawn.getX() + 32, level.getMaxBuildHeight(), spawn.getZ() + 32),
                v -> v.getTags().contains("hearthbound.restart.probe"));
        if (matches.size() != 1) return fail(source, "tagged_villager_count=" + matches.size());
        Villager sable = matches.get(0);
        var state = sable.getPersistentData();
        if (!state.contains("HearthboundHaul", 10)) return fail(source, "job_missing");
        var job = state.getCompound("HearthboundHaul");
        if (!"DELIVER".equals(job.getString("Phase")) || job.getInt("Cargo") != 4)
            return fail(source, "cargo_or_phase");
        if (state.getBoolean("HearthboundRestartInteractionStaged")
                && (!job.getBoolean("Paused") || job.getInt("InteractionTicks") != 10
                || !job.getString("InteractionPhase").equals("DELIVER")))
            return fail(source, "interaction_not_restored");
        BlockPos from = BlockPos.of(job.getLong("From"));
        sable.getPersistentData().putLong("HearthboundRestartFrom", job.getLong("From"));
        sable.getPersistentData().putLong("HearthboundRestartTo", job.getLong("To"));
        BlockPos to = BlockPos.of(job.getLong("To"));
        if (!(level.getBlockEntity(from) instanceof BarrelBlockEntity input)
                || !(level.getBlockEntity(to) instanceof BarrelBlockEntity output))
            return fail(source, "barrels_missing");
        int wheatInSource = countWheat(input);
        int wheatInOutput = countWheat(output);
        if (wheatInSource != 4 || wheatInOutput != 0
                || wheatInSource + job.getInt("Cargo") + wheatInOutput != 8)
            return fail(source, "inventory_conservation");
        var registry = WorkshopRegistry.get(level);
        var lease = registry.lease(sable.getUUID());
        if (lease == null || !lease.job().equals(job.getString("JobId"))
                || !registry.wasRestored(sable.getUUID(), job.getString("JobId")))
            return fail(source, "station_lease_not_restored");
        source.sendSuccess(() -> Component.literal("HB_RESTART_PASS source=4 cargo=4 dest=0 lease=restored interactionTicks="
                + job.getInt("InteractionTicks")), true);
        return 1;
    }

    public static int unblock(CommandSourceStack source) {
        Villager sable = findRestartCitizen(source.getLevel());
        if (sable == null) return fail(source, "villager_missing");
        var job = sable.getPersistentData().getCompound("HearthboundHaul");
        if (!"DELIVER".equals(job.getString("Phase")) || job.getInt("Cargo") != 4)
            return fail(source, "cargo_missing");
        BlockPos to = BlockPos.of(job.getLong("To"));
        if (!(source.getLevel().getBlockEntity(to) instanceof BarrelBlockEntity output))
            return fail(source, "destination_missing");
        for (int slot = 0; slot < output.getContainerSize(); slot++)
            output.setItem(slot, ItemStack.EMPTY);
        output.setChanged();
        job.putBoolean("Paused", false);
        source.sendSuccess(() -> Component.literal("HB_RESTART_UNBLOCKED"), false);
        return 1;
    }

    public static int stageInteraction(CommandSourceStack source) {
        Villager worker = findRestartCitizen(source.getLevel());
        if (worker == null || unblock(source) == 0) return fail(source, "stage_missing");
        worker.getPersistentData().putBoolean("HearthboundRestartInteractionArmed", true);
        source.sendSuccess(() -> Component.literal("HB_RESTART_INTERACTION_ARMED"), false);
        return 1;
    }

    @net.minecraftforge.eventbus.api.SubscribeEvent(priority = net.minecraftforge.eventbus.api.EventPriority.LOWEST)
    public static void observe(net.minecraftforge.event.entity.living.LivingEvent.LivingTickEvent event) {
        if (!(event.getEntity() instanceof Villager worker) || worker.level().isClientSide()) return;
        var data = worker.getPersistentData();
        if (!data.getBoolean("HearthboundRestartInteractionArmed")) return;
        var job = data.getCompound("HearthboundHaul");
        if (job.getString("Result").equals("PUTTING_DOWN") && job.getInt("InteractionTicks") == 10) {
            job.putBoolean("Paused", true);
            data.remove("HearthboundRestartInteractionArmed");
            data.putBoolean("HearthboundRestartInteractionStaged", true);
        }
    }

    public static int interactionStaged(CommandSourceStack source) {
        Villager worker = findRestartCitizen(source.getLevel());
        if (worker == null) return fail(source, "villager_missing");
        if (!worker.getPersistentData().getBoolean("HearthboundRestartInteractionStaged")) {
            source.sendSuccess(() -> Component.literal("HB_RESTART_INTERACTION_PENDING"), false);
            return 1;
        }
        if (check(source) == 0) return 0;
        source.sendSuccess(() -> Component.literal("HB_RESTART_INTERACTION_STAGED remaining=10"), false);
        return 1;
    }

    public static int delivered(CommandSourceStack source) {
        Villager sable = findRestartCitizen(source.getLevel());
        if (sable == null) return fail(source, "villager_missing");
        var data = sable.getPersistentData();
        if (data.contains("HearthboundHaul", 10)) {
            source.sendSuccess(() -> Component.literal("HB_RESTART_PENDING"), false);
            return 1;
        }
        if (!data.contains("HearthboundRestartFrom") || !data.contains("HearthboundRestartTo"))
            return fail(source, "coordinates_missing");
        BlockPos from = BlockPos.of(data.getLong("HearthboundRestartFrom"));
        BlockPos to = BlockPos.of(data.getLong("HearthboundRestartTo"));
        if (!(source.getLevel().getBlockEntity(from) instanceof BarrelBlockEntity input)
                || !(source.getLevel().getBlockEntity(to) instanceof BarrelBlockEntity output))
            return fail(source, "barrels_missing");
        if (countWheat(input) != 4 || countWheat(output) != 4
                || !"DELIVERED_4".equals(data.getString("HearthboundLastHaulResult")))
            return fail(source, "delivery_inventory_or_result");
        source.sendSuccess(() -> Component.literal("HB_RESTART_DELIVERED source=4 dest=4 cargo=0"), false);
        return 1;
    }

    private static Villager findRestartCitizen(ServerLevel level) {
        BlockPos spawn = level.getSharedSpawnPos();
        List<Villager> matches = level.getEntitiesOfClass(Villager.class,
                new AABB(spawn.getX() - 32, level.getMinBuildHeight(), spawn.getZ() - 32,
                        spawn.getX() + 32, level.getMaxBuildHeight(), spawn.getZ() + 32),
                v -> v.getTags().contains("hearthbound.restart.probe"));
        return matches.size() == 1 ? matches.get(0) : null;
    }

    private static int countWheat(BarrelBlockEntity barrel) {
        int count = 0;
        for (int i = 0; i < barrel.getContainerSize(); i++) {
            ItemStack stack = barrel.getItem(i);
            if (stack.is(Items.WHEAT)) count += stack.getCount();
        }
        return count;
    }

    private static int fail(CommandSourceStack source, String detail) {
        source.sendFailure(Component.literal("HB_RESTART_FAIL " + detail));
        return 0;
    }
}
