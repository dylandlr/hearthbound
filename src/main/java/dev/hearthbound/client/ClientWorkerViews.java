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
        final long receivedTick;
        int cargoFrames, hudFrames;
        Entry(WorkerViewPacket packet, long receivedTick) { this.packet = packet; this.receivedTick = receivedTick; }
    }
    private static final Map<Integer, Entry> VIEWS = new HashMap<>();
    private ClientWorkerViews() {}

    public static void accept(WorkerViewPacket packet) {
        var level = Minecraft.getInstance().level;
        if (level == null || !level.dimension().location().equals(packet.dimension())) return;
        var previous = VIEWS.get(packet.entityId());
        if (packet.view().visible()) {
            if (previous == null || !previous.packet.equals(packet))
                VIEWS.put(packet.entityId(), new Entry(packet, level.getGameTime()));
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
        if (entry != null && entry.cargoFrames++ == 0) recordFrame("CARGO", entry);
    }

    public static void hudRendered(Entity worker) {
        var entry = VIEWS.get(worker.getId());
        if (entry != null && entry.hudFrames++ == 0) recordFrame("HUD", entry);
    }

    public static float interactionProgress(Entity worker, float partialTick) {
        var entry = VIEWS.get(worker.getId());
        return entry == null || get(worker) == null ? 0 : Math.min(1, Math.max(0,
                (worker.level().getGameTime() - entry.receivedTick + partialTick) / 15F));
    }

    private static void recordFrame(String layer, Entry entry) {
        // Opt-in graphical acceptance evidence; ordinary clients produce no per-state logs.
        if (Boolean.getBoolean("hearthbound.recordWorkerViews"))
            org.apache.logging.log4j.LogManager.getLogger().info("HB_CLIENT_" + layer + " activity="
                    + entry.packet.view().activity() + " cargo=" + entry.packet.view().cargo());
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
