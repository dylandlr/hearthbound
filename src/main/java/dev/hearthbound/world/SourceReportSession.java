package dev.hearthbound.world;

import dev.hearthbound.evidence.ReportSessionFence;
import java.util.Map;
import java.util.UUID;
import java.util.WeakHashMap;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraftforge.event.server.ServerStartedEvent;
import net.minecraftforge.event.server.ServerStoppedEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Server-thread-only, per-server lifetime fence; never persisted as authority. */
@Mod.EventBusSubscriber(modid="hearthbound", bus=Mod.EventBusSubscriber.Bus.FORGE)
public final class SourceReportSession {
    private static final Map<MinecraftServer, ReportSessionFence> SESSIONS = new WeakHashMap<>();
    private SourceReportSession() {}

    @SubscribeEvent
    public static void started(ServerStartedEvent event) {
        var level = event.getServer().overworld();
        SESSIONS.put(event.getServer(), new ReportSessionFence(
            HearthboundWorldIdentity.get(level), UUID.randomUUID()));
    }

    @SubscribeEvent
    public static void stopped(ServerStoppedEvent event) {
        SESSIONS.remove(event.getServer());
    }

    /** Only stamp at the actual local observation, never at report delivery. */
    static void stamp(ServerLevel level, CompoundTag observation) {
        var fence = SESSIONS.get(level.getServer());
        if (fence == null || !fence.world().equals(HearthboundWorldIdentity.get(level)))
            throw new IllegalStateException("Report observation session unavailable");
        observation.putUUID("observationWorld", fence.world());
        observation.putUUID("observationSession", fence.session());
    }

    static boolean accepts(ServerLevel level, CompoundTag evidence, long delivered) {
        var fence = SESSIONS.get(level.getServer());
        return fence != null && fence.world().equals(HearthboundWorldIdentity.get(level))
            && evidence.hasUUID("observationWorld") && evidence.hasUUID("observationSession")
            && evidence.contains("observed_tick", Tag.TAG_LONG)
            && fence.accepts(evidence.getUUID("observationWorld"),
                evidence.getUUID("observationSession"), evidence.getLong("observed_tick"),
                delivered, level.getGameTime());
    }
}
