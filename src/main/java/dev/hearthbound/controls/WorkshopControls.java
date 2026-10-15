package dev.hearthbound.controls;

import java.util.Map;
import java.util.WeakHashMap;
import java.util.UUID;
import dev.hearthbound.jobs.FirstMillWorkOrder;
import dev.hearthbound.jobs.SableSelection;
import dev.hearthbound.presentation.WorkerPresentation;
import dev.hearthbound.presentation.WorkerViewPacket;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.resources.ResourceLocation;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.network.PacketDistributor;

/** Every mutation resolves the exact server entity and rechecks access, range and revision. */
public final class WorkshopControls {
    private record Session(UUID worker, ResourceLocation dimension, long expires) {}
    private static final Map<ServerPlayer, Session> SESSIONS = new WeakHashMap<>();
    private WorkshopControls() {}

    public static boolean canEdit(ServerPlayer player, Villager worker) {
        var data = worker.getPersistentData();
        UUID owner = data.hasUUID("HearthboundSupervisor") ? data.getUUID("HearthboundSupervisor") : null;
        return !player.isSpectator() && player.getAbilities().mayBuild
                && WorkshopAccess.canManage(owner, player.getUUID(), player.hasPermissions(2), SableSelection.idle(worker));
    }

    public static void handle(ServerPlayer player, WorkshopAction request) {
        var level = player.serverLevel();
        if (!(level.getEntity(request.worker()) instanceof Villager worker) || !worker.isAlive()
                || !worker.getTags().contains("hearthbound.sable")) return;
        if (request.action() == WorkshopAction.OPEN) {
            if (player.distanceToSqr(worker) > 36 || !player.hasLineOfSight(worker) || !player.getMainHandItem().isEmpty()) return;
            SESSIONS.put(player, new Session(worker.getUUID(), level.dimension().location(), level.getGameTime() + 6000));
            reply(player, worker, ""); return;
        }
        var session = SESSIONS.get(player);
        if (session == null || !session.worker().equals(worker.getUUID())
                || !session.dimension().equals(level.dimension().location())) return;
        if (request.action() == WorkshopAction.CLOSE) { SESSIONS.remove(player); return; }
        if (level.getGameTime() > session.expires() || player.distanceToSqr(worker) > 32 * 32) {
            SESSIONS.remove(player);
            player.displayClientMessage(net.minecraft.network.chat.Component.literal("Move closer to Sable and reopen the workshop."), true); return;
        }
        if (request.action() == WorkshopAction.REFRESH) {
            SESSIONS.put(player, new Session(worker.getUUID(), level.dimension().location(), level.getGameTime() + 6000));
            reply(player, worker, ""); return;
        }
        if (!canEdit(player, worker)) { reply(player, worker, "Only the supervisor or a server operator can edit this worker."); return; }
        if (request.revision() != FirstMillWorkOrder.revision(worker)) {
            reply(player, worker, "The order changed. Review the current setup and try again."); return;
        }
        if (request.action() == WorkshopAction.STOP) {
            if (worker.getPersistentData().contains("HearthboundMillOrder", 10)) FirstMillWorkOrder.stopWorker(worker);
            reply(player, worker, "Scheduling stopped. The current haul will finish."); return;
        }
        if (request.action() != WorkshopAction.SAVE) return;
        for (BlockPos point : new BlockPos[] {request.wheat(), request.mill(), request.flour(), request.waiting()}) {
            if (point != null && (point.getY() < level.getMinBuildHeight() || point.getY() >= level.getMaxBuildHeight()
                    || !level.hasChunkAt(point) || worker.distanceToSqr(point.getX() + .5, point.getY(), point.getZ() + .5) > 32 * 32
                    || !level.mayInteract(player, point))) {
                reply(player, worker, "Choose loaded stations and floor within 32 blocks of Sable where you can build."); return;
            }
        }
        boolean existing = worker.getPersistentData().contains("HearthboundMillOrder", 10);
        String error = FirstMillWorkOrder.configure(worker, request.wheat(), request.mill(), request.flour(), request.waiting(), request.target());
        if (!error.isEmpty()) { reply(player, worker, error); return; }
        if (!existing && !worker.getPersistentData().hasUUID("HearthboundSupervisor"))
            worker.getPersistentData().putUUID("HearthboundSupervisor", player.getUUID());
        reply(player, worker, existing ? "Workshop changes saved." : "Work order started.");
        SESSIONS.put(player, new Session(worker.getUUID(), level.dimension().location(), level.getGameTime() + 6000));
    }

    private static void reply(ServerPlayer player, Villager worker, String notice) {
        var data = worker.getPersistentData();
        var source = data.getCompound(data.contains("HearthboundMillOrder", 10) ? "HearthboundMillOrder" : "HearthboundWorkshopSetup");
        var settings = new CompoundTag();
        for (String key : new String[] {"Wheat", "Mill", "Flour", "Wait"})
            if (source.contains(key, 4)) settings.putLong(key, source.getLong(key));
        settings.putInt("TargetFlour", source.contains("TargetFlour") ? source.getInt("TargetFlour") : 16);
        var view = WorkerPresentation.inspect(worker);
        var packet = new WorkerViewPacket(worker.getId(), worker.getUUID(), worker.level().dimension().location(), view);
        String name = worker.getName().getString(); if (name.length() > 128) name = name.substring(0, 128);
        WorkshopNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), new WorkshopSnapshot(packet, name,
                canEdit(player, worker), data.contains("HearthboundHaul", 10) || data.getBoolean("HearthboundTravelActive"),
                FirstMillWorkOrder.revision(worker), settings, notice));
    }
}
