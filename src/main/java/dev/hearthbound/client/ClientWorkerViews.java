package dev.hearthbound.client;

import java.util.HashMap;
import java.util.Map;
import dev.hearthbound.HearthboundMod;
import dev.hearthbound.presentation.WorkerView;
import dev.hearthbound.presentation.WorkerViewPacket;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.Entity;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.ClientPlayerNetworkEvent;
import net.minecraftforge.client.event.RegisterClientCommandsEvent;
import net.minecraftforge.event.entity.EntityLeaveLevelEvent;
import net.minecraftforge.event.level.LevelEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Main-client-thread cache, checked against dimension and UUID to reject recycled entity IDs. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID, value = Dist.CLIENT)
public final class ClientWorkerViews {
    private static final class Entry {
        final WorkerViewPacket packet;
        int cargoFrames, hudFrames;
        Entry(WorkerViewPacket packet) { this.packet = packet; }
    }
    private static final Map<Integer, Entry> VIEWS = new HashMap<>();
    private ClientWorkerViews() {}

    public static void accept(WorkerViewPacket packet) {
        var level = Minecraft.getInstance().level;
        if (level == null || !level.dimension().location().equals(packet.dimension())) return;
        var previous = VIEWS.get(packet.entityId());
        if (packet.view().visible()) {
            if (previous == null || !previous.packet.equals(packet))
                VIEWS.put(packet.entityId(), new Entry(packet));
        }
        else if (previous != null && previous.packet.workerId().equals(packet.workerId()))
            VIEWS.remove(packet.entityId());
    }

    public static WorkerView get(Entity entity) {
        var entry = VIEWS.get(entity.getId());
        var packet = entry == null ? null : entry.packet;
        return packet != null && packet.workerId().equals(entity.getUUID())
                && packet.dimension().equals(entity.level().dimension().location()) ? packet.view() : null;
    }

    public static void cargoRendered(Entity worker) {
        var entry = VIEWS.get(worker.getId());
        if (entry != null) entry.cargoFrames++;
    }

    public static void hudRendered(Entity worker) {
        var entry = VIEWS.get(worker.getId());
        if (entry != null) entry.hudFrames++;
    }

    /** Explicit diagnostic for real client playtests; reads only received/rendered state. */
    @SubscribeEvent
    public static void commands(RegisterClientCommandsEvent event) {
        event.getDispatcher().register(net.minecraft.commands.Commands.literal("hearthbound_client_view")
                .executes(context -> {
                    var mc = Minecraft.getInstance();
                    if (!(mc.hitResult instanceof net.minecraft.world.phys.EntityHitResult hit)
                            || get(hit.getEntity()) == null) {
                        context.getSource().sendFailure(net.minecraft.network.chat.Component.literal("Look at a colony worker."));
                        return 0;
                    }
                    var entry = VIEWS.get(hit.getEntity().getId());
                    var view = entry.packet.view();
                    String result = "HB_CLIENT_VIEW activity=" + view.activity() + " cargo=" + view.cargo()
                            + " item=" + view.item() + " flour=" + view.stockedFlour()
                            + " target=" + view.targetFlour() + " cargoFrames=" + entry.cargoFrames
                            + " hudFrames=" + entry.hudFrames;
                    context.getSource().sendSuccess(() -> net.minecraft.network.chat.Component.literal(result), false);
                    org.apache.logging.log4j.LogManager.getLogger().info(result);
                    return 1;
                }));
    }

    @SubscribeEvent
    public static void leave(EntityLeaveLevelEvent event) {
        if (event.getLevel().isClientSide()) {
            var entry = VIEWS.get(event.getEntity().getId());
            if (entry != null && entry.packet.workerId().equals(event.getEntity().getUUID()))
                VIEWS.remove(event.getEntity().getId());
        }
    }

    @SubscribeEvent
    public static void unload(LevelEvent.Unload event) {
        if (event.getLevel().isClientSide()) VIEWS.clear();
    }

    @SubscribeEvent
    public static void logout(ClientPlayerNetworkEvent.LoggingOut event) { VIEWS.clear(); }
}
