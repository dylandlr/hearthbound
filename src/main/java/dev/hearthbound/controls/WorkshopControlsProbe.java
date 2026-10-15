package dev.hearthbound.controls;

import java.util.UUID;
import dev.hearthbound.jobs.FirstMillWorkOrder;
import dev.hearthbound.jobs.SableSelection;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;

/** Negative request checks using the real connected UI player's existing session. */
public final class WorkshopControlsProbe {
    private WorkshopControlsProbe() {}
    public static int run(CommandSourceStack source) {
        var player = source.getServer().getPlayerList().getPlayerByName("HearthboundQA");
        var worker = SableSelection.nearest(source, w -> w.getPersistentData().contains("HearthboundMillOrder", 10));
        if (player == null || worker == null || player.hasPermissions(2)
                || !worker.getPersistentData().hasUUID("HearthboundSupervisor")
                || !worker.getPersistentData().getUUID("HearthboundSupervisor").equals(player.getUUID())) return fail(source, "normal_supervisor_required");
        var data = worker.getPersistentData(); var before = data.copy();
        var order = data.getCompound("HearthboundMillOrder"); long revision = FirstMillWorkOrder.revision(worker);
        BlockPos wheat = BlockPos.of(order.getLong("Wheat")), mill = BlockPos.of(order.getLong("Mill")), flour = BlockPos.of(order.getLong("Flour"));
        BlockPos wait = BlockPos.of(order.getLong("Wait"));
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.STOP, revision - 1, null, null, null, null, 0, null));
        if (!before.equals(data)) return fail(source, "stale_revision_mutated_state");
        WorkshopControls.handle(player, new WorkshopAction(UUID.randomUUID(), WorkshopAction.STOP, revision, null, null, null, null, 0, null));
        if (!before.equals(data)) return fail(source, "wrong_worker_mutated_state");
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.SAVE, revision, wheat, mill, flour, wait, 4097, null));
        if (!before.equals(data)) return fail(source, "invalid_target_mutated_state");
        BlockPos unloaded = new BlockPos(29000000, 100, 29000000);
        if (source.getLevel().hasChunkAt(unloaded)) return fail(source, "negative_point_already_loaded");
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.SAVE, revision, unloaded, mill, flour, wait, 2, null));
        if (!before.equals(data) || source.getLevel().hasChunkAt(unloaded)) return fail(source, "unloaded_point_mutated_or_loaded");
        var registry = dev.hearthbound.jobs.WorkshopRegistry.get(source.getLevel());
        var registryBefore = registry.save(new net.minecraft.nbt.CompoundTag());
        var status = WorkshopStatus.inspect(worker, player.getUUID(), false, unloaded, unloaded, unloaded);
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.REFRESH, revision,
                unloaded, unloaded, unloaded, null, 0, null));
        if (status.access() != WorkshopStatus.Access.UNAVAILABLE || status.mill().state() != WorkshopStatus.State.UNAVAILABLE
                || source.getLevel().hasChunkAt(unloaded) || !before.equals(data)
                || !registryBefore.equals(registry.save(new net.minecraft.nbt.CompoundTag())))
            return fail(source, "preview_loaded_or_mutated");
        source.sendSuccess(() -> Component.literal("HB_WORKSHOP_STATUS_PREVIEW_PASS unloaded_rejected readonly_no_claim_or_reservation"), false);
        UUID owner = data.getUUID("HearthboundSupervisor");
        data.putUUID("HearthboundSupervisor", UUID.randomUUID());
        var strangerBefore = data.copy();
        try {
            WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.STOP, revision, null, null, null, null, 0, null));
            if (!strangerBefore.equals(data)) return fail(source, "stranger_stopped_order");
        } finally { data.putUUID("HearthboundSupervisor", owner); }
        if (!before.equals(data)) return fail(source, "state_not_restored");
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.REFRESH, revision, wheat, mill, flour, wait, 0, null));
        source.sendSuccess(() -> Component.literal("HB_WORKSHOP_CONTROLS_AUTH_PASS non_operator_owner stale_revision wrong_worker invalid_target unloaded_point stranger_denied cargo_unchanged"), false);
        return 1;
    }
    public static int withoutCreate(CommandSourceStack source) {
        var level = source.getLevel();
        var key = new net.minecraft.resources.ResourceLocation("create", "millstone");
        if (net.minecraft.core.registries.BuiltInRegistries.BLOCK.containsKey(key)) return fail(source, "expected_optional_create_absence");
        BlockPos from = new BlockPos(2, 100, 2), mill = new BlockPos(4, 100, 2), to = new BlockPos(6, 100, 2);
        if (!level.hasChunkAt(from)) return fail(source, "negative_fixture_chunk_missing");
        level.setBlockAndUpdate(from, net.minecraft.world.level.block.Blocks.BARREL.defaultBlockState());
        level.setBlockAndUpdate(to, net.minecraft.world.level.block.Blocks.BARREL.defaultBlockState());
        level.setBlockAndUpdate(mill, net.minecraft.world.level.block.Blocks.AIR.defaultBlockState());
        var input = (net.minecraft.world.level.block.entity.BarrelBlockEntity) level.getBlockEntity(from);
        var output = (net.minecraft.world.level.block.entity.BarrelBlockEntity) level.getBlockEntity(to);
        input.setItem(0, new net.minecraft.world.item.ItemStack(net.minecraft.world.item.Items.WHEAT, 8));
        var worker = net.minecraft.world.entity.EntityType.VILLAGER.create(level);
        if (worker == null) return fail(source, "worker_fixture_missing");
        String error = FirstMillWorkOrder.configure(worker, from, mill, to, null, 2);
        if (error.isEmpty() || worker.getPersistentData().contains("HearthboundMillOrder", 10)
                || input.getItem(0).getCount() != 8 || !output.isEmpty()) return fail(source, "air_accepted_without_create");
        source.sendSuccess(() -> Component.literal("HB_WORKSHOP_OPTIONAL_CREATE_PASS air_rejected no_order no_extraction"), false);
        return 1;
    }

    private static int fail(CommandSourceStack source, String reason) {
        source.sendFailure(Component.literal("HB_WORKSHOP_CONTROLS_AUTH_FAIL " + reason)); return 0;
    }
}
