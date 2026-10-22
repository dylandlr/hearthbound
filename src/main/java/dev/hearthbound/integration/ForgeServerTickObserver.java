package dev.hearthbound.integration;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
/** Drives the overworld SavedData counter once per completed logical-server tick. */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ForgeServerTickObserver {
    private ForgeServerTickObserver() {}
    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        long tick = HearthboundClockSavedData.get(event.getServer()).advance();
        for (var level : event.getServer().getAllLevels()) MillstoneTrace.sample(level, tick);
    }
    public static long logicalTick(net.minecraft.server.MinecraftServer server) {
        return HearthboundClockSavedData.get(server).tick();
    }
}