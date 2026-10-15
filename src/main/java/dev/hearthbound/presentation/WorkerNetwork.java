package dev.hearthbound.presentation;

import dev.hearthbound.HearthboundMod;
import dev.hearthbound.client.ClientWorkerViews;
import net.minecraft.resources.ResourceLocation;
import net.minecraftforge.api.distmarker.Dist;
import net.minecraftforge.fml.DistExecutor;
import net.minecraftforge.network.NetworkDirection;
import net.minecraftforge.network.NetworkRegistry;
import net.minecraftforge.network.simple.SimpleChannel;

public final class WorkerNetwork {
    private static final String VERSION = "1";
    public static final SimpleChannel CHANNEL = NetworkRegistry.newSimpleChannel(
            new ResourceLocation(HearthboundMod.MOD_ID, "worker_view"), () -> VERSION,
            VERSION::equals, VERSION::equals);

    private WorkerNetwork() {}

    public static void register() {
        CHANNEL.messageBuilder(WorkerViewPacket.class, 0, NetworkDirection.PLAY_TO_CLIENT)
                .encoder(WorkerViewPacket::encode).decoder(WorkerViewPacket::decode)
                .consumerMainThread((message, context) -> DistExecutor.unsafeRunWhenOn(Dist.CLIENT,
                        () -> () -> ClientWorkerViews.accept(message)))
                .add();
    }
}
