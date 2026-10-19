package dev.hearthbound.research;

import dev.hearthbound.world.CitizenWorkOwnership;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Server-authoritative hook: never grant learning from an unverified client packet. */
@Mod.EventBusSubscriber(modid = "hearthbound")
public final class LibraryStudyEvents {
    private LibraryStudyEvents() {}

    @SubscribeEvent
    public static void onLivingTick(LivingEvent.LivingTickEvent event) {
        if (event.getEntity() instanceof Villager citizen
                && citizen.level() instanceof ServerLevel level) {
            if (dev.hearthbound.world.CitizenSurvival.paused(citizen)) return;
            AutonomousLibraryStudy.tick(level, citizen);
            LibraryStudyRuntime.tick(level, citizen);
            LibraryPolicyBridge.reconcile(citizen);
            CitizenWorkOwnership.reconcile(citizen);
            LibraryAutonomyTick.tick(level, citizen);
        }
    }
}
