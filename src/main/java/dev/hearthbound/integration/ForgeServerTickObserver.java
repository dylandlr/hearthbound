package dev.hearthbound.integration;

import dev.hearthbound.research.ServerTickClock;
import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Observes Forge's server tick; does not infer Create processing completions. */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ForgeServerTickObserver {
    private static ServerTickClock clock = new ServerTickClock(0);
    private ForgeServerTickObserver() {}
    @SubscribeEvent
    public static void onServerTick(TickEvent.ServerTickEvent event) {
        if (event.phase != TickEvent.Phase.END) return;
        clock.observe(event.getServer().getTickCount());
    }
    /** In-memory only; future SavedData adapter must persist the logical tick. */
    public static long logicalTick() { return clock.current(); }
}
