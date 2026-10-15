package dev.hearthbound.presentation;

import java.util.Map;
import java.util.WeakHashMap;
import dev.hearthbound.HearthboundMod;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.event.entity.player.PlayerEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraftforge.network.PacketDistributor;

/** State changes reach tracking players; late viewers receive a fresh initial snapshot. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class WorkerViewSync {
    private static final Map<Villager, WorkerView> LAST = new WeakHashMap<>();
    private WorkerViewSync() {}

    private static WorkerViewPacket packet(Villager worker, WorkerView view) {
        return new WorkerViewPacket(worker.getId(), worker.getUUID(), worker.level().dimension().location(), view);
    }

    @SubscribeEvent(priority = EventPriority.LOWEST)
    public static void tick(LivingEvent.LivingTickEvent event) {
        if (!(event.getEntity() instanceof Villager worker) || !(worker.level() instanceof ServerLevel)
                || worker.tickCount % 5 != 0) return;
        if (!worker.getTags().contains("hearthbound.sable") && !LAST.containsKey(worker)) return;
        var view = WorkerPresentation.inspect(worker);
        if (!view.equals(LAST.get(worker)) || worker.tickCount % 100 == 0)
            WorkerNetwork.CHANNEL.send(PacketDistributor.TRACKING_ENTITY.with(() -> worker), packet(worker, view));
        if (view.visible()) LAST.put(worker, view);
        else LAST.remove(worker);
    }

    @SubscribeEvent
    public static void startTracking(PlayerEvent.StartTracking event) {
        if (event.getEntity() instanceof ServerPlayer player && event.getTarget() instanceof Villager worker
                && worker.getTags().contains("hearthbound.sable"))
            WorkerNetwork.CHANNEL.send(PacketDistributor.PLAYER.with(() -> player),
                    packet(worker, WorkerPresentation.inspect(worker)));
    }
}
