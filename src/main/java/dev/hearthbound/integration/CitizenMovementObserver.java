package dev.hearthbound.integration;

import net.minecraftforge.event.TickEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;
import net.minecraft.core.BlockPos;
import java.util.UUID;

/** First server-authoritative Hearthbound movement loop over loaded vanilla villagers. */
@Mod.EventBusSubscriber(modid="hearthbound",bus=Mod.EventBusSubscriber.Bus.FORGE)
public final class CitizenMovementObserver {
    private CitizenMovementObserver() {}
    @SubscribeEvent
    public static void tick(TickEvent.ServerTickEvent event) {
        if(event.phase!=TickEvent.Phase.END) return;
        var server=event.getServer();
        long tick=ForgeServerTickObserver.logicalTick(server);
        if(tick%10!=0) return;
        var registry=CitizenRegistrySavedData.get(server);
        for(var citizen:registry.snapshot()) {
            if(!citizen.task().startsWith("MOVE:")) continue;
            var level=server.getLevel(net.minecraft.resources.ResourceKey.create(
                    net.minecraft.core.registries.Registries.DIMENSION,
                    new net.minecraft.resources.ResourceLocation(citizen.dimension())));
            if(level==null)continue;
            var villager=CitizenEmbodiment.find(level,citizen.id());
            if(villager==null || !villager.isAlive())continue;
            long encoded;
            try {encoded=Long.parseLong(citizen.task().substring(5));}
            catch(NumberFormatException badTask){continue;}
            BlockPos target=BlockPos.of(encoded);
            boolean arrived=villager.blockPosition().distSqr(target)<=4;
            if(!arrived) villager.getNavigation().moveTo(
                    target.getX()+0.5,target.getY(),target.getZ()+0.5,0.7);
            registry.observe(citizen.id(),villager.blockPosition().asLong(),tick,arrived);
            if(arrived) org.apache.logging.log4j.LogManager.getLogger().info(
                    "HEARTHBOUND_CITIZEN_ARRIVED citizen={} pos={} tick={}",
                    citizen.id(),villager.blockPosition(),tick);
        }
    }
}
