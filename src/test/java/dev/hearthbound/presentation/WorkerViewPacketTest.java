package dev.hearthbound.presentation;

import io.netty.buffer.Unpooled;
import java.util.UUID;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class WorkerViewPacketTest {
    @Test void flourCargoAndOrderSurviveTheWire() {
        roundTrip(new WorkerView(true, "create:wheat_flour", 1, "delivering", true, 17, 4096));
    }

    @Test void missingStockAndFullCargoSurviveTheWire() {
        roundTrip(new WorkerView(true, "minecraft:wheat", 64, "output_full", true, -1, 0));
    }

    @Test void clearStateSurvivesTheWire() {
        roundTrip(new WorkerView(false, "minecraft:air", 0, "idle", false, -1, 0));
    }

    private static void roundTrip(WorkerView view) {
        var original = new WorkerViewPacket(1923, UUID.randomUUID(), new ResourceLocation("minecraft", "the_nether"), view);
        var buffer = new FriendlyByteBuf(Unpooled.buffer());
        try {
            original.encode(buffer);
            assertEquals(original, WorkerViewPacket.decode(buffer));
            assertEquals(0, buffer.readableBytes(), "Packet must consume its exact payload");
        } finally { buffer.release(); }
    }
}
