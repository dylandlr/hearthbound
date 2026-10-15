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
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.STOP, revision - 1, null, null, null, null, 0));
        if (!before.equals(data)) return fail(source, "stale_revision_mutated_state");
        WorkshopControls.handle(player, new WorkshopAction(UUID.randomUUID(), WorkshopAction.STOP, revision, null, null, null, null, 0));
        if (!before.equals(data)) return fail(source, "wrong_worker_mutated_state");
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.SAVE, revision, wheat, mill, flour, wait, 4097));
        if (!before.equals(data)) return fail(source, "invalid_target_mutated_state");
        BlockPos unloaded = new BlockPos(29000000, 100, 29000000);
        if (source.getLevel().hasChunkAt(unloaded)) return fail(source, "negative_point_already_loaded");
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.SAVE, revision, unloaded, mill, flour, wait, 2));
        if (!before.equals(data) || source.getLevel().hasChunkAt(unloaded)) return fail(source, "unloaded_point_mutated_or_loaded");
        UUID owner = data.getUUID("HearthboundSupervisor");
        data.putUUID("HearthboundSupervisor", UUID.randomUUID());
        var strangerBefore = data.copy();
        try {
            WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.STOP, revision, null, null, null, null, 0));
            if (!strangerBefore.equals(data)) return fail(source, "stranger_stopped_order");
        } finally { data.putUUID("HearthboundSupervisor", owner); }
        if (!before.equals(data)) return fail(source, "state_not_restored");
        WorkshopControls.handle(player, new WorkshopAction(worker.getUUID(), WorkshopAction.REFRESH, revision, null, null, null, null, 0));
        source.sendSuccess(() -> Component.literal("HB_WORKSHOP_CONTROLS_AUTH_PASS non_operator_owner stale_revision wrong_worker invalid_target unloaded_point stranger_denied cargo_unchanged"), false);
        return 1;
    }
    private static int fail(CommandSourceStack source, String reason) {
        source.sendFailure(Component.literal("HB_WORKSHOP_CONTROLS_AUTH_FAIL " + reason)); return 0;
    }
}
