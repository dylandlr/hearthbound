package dev.hearthbound.client;

import dev.hearthbound.HearthboundMod;
import net.minecraft.client.renderer.entity.VillagerRenderer;
import net.minecraft.world.entity.EntityType;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.client.event.EntityRenderersEvent;
import net.minecraftforge.eventbus.api.SubscribeEvent;
import net.minecraftforge.fml.common.Mod;

@Mod.EventBusSubscriber(modid = HearthboundMod.MOD_ID, bus = Mod.EventBusSubscriber.Bus.MOD, value = Dist.CLIENT)
public final class WorkerClientSetup {
    private WorkerClientSetup() {}

    @SubscribeEvent
    public static void layers(EntityRenderersEvent.AddLayers event) {
        var renderer = event.getEntityRenderer(EntityType.VILLAGER);
        if (renderer instanceof VillagerRenderer villager)
            villager.addLayer(new WorkerCargoLayer(villager, event.getContext().getItemInHandRenderer()));
    }
}
