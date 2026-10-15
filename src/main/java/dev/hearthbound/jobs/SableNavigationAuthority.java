package dev.hearthbound.jobs;

import dev.hearthbound.HearthboundMod;
import java.util.Collections;
import java.util.Set;
import java.util.WeakHashMap;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.ai.memory.MemoryModuleType;
import net.minecraft.world.entity.npc.Villager;
import net.minecraftforge.event.entity.living.LivingEvent;
import net.minecraftforge.eventbus.api.EventPriority;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

/** Gives colony jobs exclusive navigation control while preserving normal mob physics. */
@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID)
public final class SableNavigationAuthority {
    // Loaded entity identity only: persisted jobs reconstruct ownership after reload.
    private static final Set<Villager> OWNED = Collections.newSetFromMap(new WeakHashMap<>());

    private SableNavigationAuthority() {}

    @SubscribeEvent(priority = EventPriority.HIGHEST)
    public static void tick(LivingEvent.LivingTickEvent event) {
        if (!(event.getEntity() instanceof Villager worker)
                || !(worker.level() instanceof ServerLevel level)
                || !worker.getTags().contains("hearthbound.sable")) return;
        var data = worker.getPersistentData();
        boolean assigned = data.contains("HearthboundHaul", 10)
                || data.contains("HearthboundMillOrder", 10)
                || data.getBoolean("HearthboundTravelActive");
        if (assigned) {
            var brain = worker.getBrain();
            // Vanilla idle/work/POI behaviors otherwise replace the route between
            // our bounded job ticks. Do not disable NoAI: navigation and physics
            // must continue to execute on the real villager.
            brain.stopAll(level, worker);
            brain.removeAllBehaviors();
            brain.eraseMemory(MemoryModuleType.WALK_TARGET);
            brain.eraseMemory(MemoryModuleType.PATH);
            OWNED.add(worker);
        } else if (OWNED.remove(worker)) {
            worker.getNavigation().stop();
            worker.refreshBrain(level);
        }
    }
}
