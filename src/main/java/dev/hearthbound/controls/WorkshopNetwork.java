package dev.hearthbound.controls;

import dev.hearthbound.HearthboundMod;
import dev.hearthbound.client.ClientWorkshop;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;

public final class WorkshopNetwork {
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(HearthboundMod.MOD_ID, "workshop_controls"), () -> "1", "1"::equals, "1"::equals);
    private WorkshopNetwork() {}
    public static void register() {
        CHANNEL.messageBuilder(WorkshopAction.class, 0, NetworkDirection.PLAY_TO_SERVER)
                .encoder(WorkshopAction::encode).decoder(WorkshopAction::decode)
                .consumerMainThread((m, c) -> { var player = c.get().getSender(); if (player != null) WorkshopControls.handle(player, m); }).add();
        CHANNEL.messageBuilder(WorkshopSnapshot.class, 1, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(WorkshopSnapshot::encode).decoder(WorkshopSnapshot::decode)
                .consumerMainThread((m, c) -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT, () -> () -> ClientWorkshop.accept(m))).add();
    }
}
