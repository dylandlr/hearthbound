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
            reply(player, worker, "", request); return;
        }
        if (request.action() == WorkshopAction.SHARE || request.action() == WorkshopAction.REVOKE
                || request.action() == WorkshopAction.RELEASE) {
            handleAccess(player, worker, request); return;
        }
        if (!canEdit(player, worker)) { reply(player, worker, "Only the supervisor or a server operator can edit this worker."); return; }
        if (request.revision() != FirstMillWorkOrder.revision(worker)) {
            reply(player, worker, "The order changed. Review the current setup and try again."); return;
        }
        if (request.action() == WorkshopAction.STOP) {
            if (worker.getPersistentData().contains("HearthboundMillOrder", 10)) FirstMillWorkOrder.stopWorker(worker);
            reply(player, worker, "Scheduling stopped. The current haul will finish."); return;
        }
        if (request.action() == WorkshopAction.RESUME) {
            var data = worker.getPersistentData();
            if (data.contains("HearthboundHaul", 10) && data.getCompound("HearthboundHaul").getBoolean("Paused")) {
                data.getCompound("HearthboundHaul").putBoolean("Paused", false);
                FirstMillWorkOrder.advanceRevision(worker);
                reply(player, worker, "Haul resumed.");
            } else reply(player, worker, "The current haul is not paused.");
            return;
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
        String error = FirstMillWorkOrder.configureFor(worker, request.wheat(), request.mill(), request.flour(), request.waiting(), request.target(),
                player.getUUID(), player.hasPermissions(2));
        if (!error.isEmpty()) { reply(player, worker, error); return; }
        if (!existing && !worker.getPersistentData().hasUUID("HearthboundSupervisor"))
            worker.getPersistentData().putUUID("HearthboundSupervisor", player.getUUID());
        reply(player, worker, existing ? "Workshop changes saved." : "Work order started.");
        SESSIONS.put(player, new Session(worker.getUUID(), level.dimension().location(), level.getGameTime() + 6000));
    }

    private static void handleAccess(ServerPlayer player, Villager worker, WorkshopAction request) {
        var level = player.serverLevel(); BlockPos mill = request.mill();
        if (request.revision() != FirstMillWorkOrder.revision(worker)) {
            reply(player, worker, "The order changed. Review the current setup and try again.", request); return;
        }
        if (player.isSpectator() || !player.getAbilities().mayBuild || mill == null
                || !WorkshopStatus.available(level, worker, mill, true) || !level.mayInteract(player, mill)) {
            reply(player, worker, "Move closer to the loaded millstone where you can build.", request); return;
        }
        var registry = dev.hearthbound.jobs.WorkshopRegistry.get(level);
        if (registry.owner(mill) == null) {
            reply(player, worker, "Start an order before managing workshop access.", request); return;
        }
        boolean operator = player.hasPermissions(2);
        if (!registry.canManage(mill, player.getUUID(), operator)) {
            reply(player, worker, "Only the mill owner or a server operator can manage access.", request); return;
        }
        if (request.action() == WorkshopAction.RELEASE) {
            if (!registry.release(mill, player.getUUID(), operator)) {
                reply(player, worker, "Finish the reserved haul before releasing this workshop.", request); return;
            }
            reply(player, worker, "Workshop ownership and sharing released.", request); return;
        }
        UUID member = request.player();
        if (member == null) { reply(player, worker, "Choose a player first.", request); return; }
        if (request.action() == WorkshopAction.SHARE) {
            var target = level.getServer().getPlayerList().getPlayer(member);
            if (target == null || target.isSpectator()) {
                reply(player, worker, "That player must be online to receive access.", request); return;
            }
            if (!registry.share(mill, player.getUUID(), member, operator)) {
                reply(player, worker, "Access was not changed. A mill can have up to "
                        + dev.hearthbound.jobs.WorkshopRegistry.MAX_SHARED + " collaborators.", request); return;
            }
            reply(player, worker, "Workshop access shared with " + target.getName().getString() + ".", request); return;
        }
        if (!registry.revoke(mill, player.getUUID(), member, operator)) {
            reply(player, worker, "That player does not have shared access.", request); return;
        }
        reply(player, worker, "Shared access revoked. Active cargo and reservations are retained.", request);
    }

    private static void reply(ServerPlayer player, Villager worker, String notice) { reply(player, worker, notice, null); }

    private static void reply(ServerPlayer player, Villager worker, String notice, WorkshopAction preview) {
        var data = worker.getPersistentData();
        var source = data.getCompound(data.contains("HearthboundMillOrder", 10) ? "HearthboundMillOrder" : "HearthboundWorkshopSetup");
        var settings = new CompoundTag();
        for (String key : new String[] {"Wheat", "Mill", "Flour", "Wait"})
            if (source.contains(key, 4)) settings.putLong(key, source.getLong(key));
        settings.putInt("TargetFlour", source.contains("TargetFlour") ? source.getInt("TargetFlour") : 16);
        BlockPos wheat = preview == null ? savedPoint(settings, "Wheat") : preview.wheat();
        BlockPos mill = preview == null ? savedPoint(settings, "Mill") : preview.mill();
        BlockPos flour = preview == null ? savedPoint(settings, "Flour") : preview.flour();
        var status = WorkshopStatus.inspect(worker, player.getUUID(), player.hasPermissions(2), wheat, mill, flour);
        var view = WorkerPresentation.inspect(worker);
        var packet = new WorkerViewPacket(worker.getId(), worker.getUUID(), worker.level().dimension().location(), view);
        String name = worker.getName().getString(); if (name.length() > 128) name = name.substring(0, 128);
        WorkshopNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player), new WorkshopSnapshot(packet, name,
                canEdit(player, worker), data.contains("HearthboundHaul", 10) || data.getBoolean("HearthboundTravelActive"),
                FirstMillWorkOrder.revision(worker), settings, status, notice));
    }

    private static BlockPos savedPoint(CompoundTag settings, String key) {
        return settings.contains(key, 4) ? BlockPos.of(settings.getLong(key)) : null;
    }
}
