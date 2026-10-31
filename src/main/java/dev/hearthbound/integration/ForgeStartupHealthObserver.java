package dev.hearthbound.integration;

import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.ModList;
import net.minecraftforge.fml.common.Mod;
import org.apache.logging.log4j.LogManager;
import org.apache.logging.log4j.Logger;

/**
 * Server readiness marker emitted only after Forge reaches ServerStartedEvent.
 * The smoke workflow requires this marker in addition to Minecraft's "Done".
 */
@Mod.EventBusSubscriber(modid = "hearthbound", bus = Mod.EventBusSubscriber.Bus.FORGE)
public final class ForgeStartupHealthObserver {
    private static final Logger LOGGER = LogManager.getLogger();
    private ForgeStartupHealthObserver() {}

    @SubscribeEvent
    public static void serverStarted(ServerStartedEvent event) {
        boolean createLoaded = ModList.get().isLoaded("create");
        long tick = HearthboundClockSavedData.get(event.getServer()).tick();
        LOGGER.info("HEARTHBOUND_SERVER_READY createLoaded={} logicalTick={} researchBridge=not-connected",
                createLoaded, tick);
        if (!createLoaded) LOGGER.error("Hearthbound startup: mandatory Create dependency is missing");
    }
}
