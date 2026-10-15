package dev.hearthbound.presentation;

import java.util.UUID;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;

/** Clientbound only; carries identifiers and counts, never an ItemStack. */
public record WorkerViewPacket(int entityId, UUID workerId, ResourceLocation dimension, WorkerView view) {
    public void encode(FriendlyByteBuf buf) {
        buf.writeVarInt(entityId);
        buf.writeUUID(workerId);
        buf.writeResourceLocation(dimension);
        buf.writeBoolean(view.visible());
        buf.writeUtf(view.item(), 128);
        buf.writeVarInt(view.cargo());
        buf.writeUtf(view.activity(), 64);
        buf.writeBoolean(view.hasOrder());
        buf.writeVarInt(view.stockedFlour());
        buf.writeVarInt(view.targetFlour());
    }

    public static WorkerViewPacket decode(FriendlyByteBuf buf) {
        return new WorkerViewPacket(buf.readVarInt(), buf.readUUID(), buf.readResourceLocation(),
                new WorkerView(buf.readBoolean(), buf.readUtf(128), buf.readVarInt(), buf.readUtf(64),
                        buf.readBoolean(), buf.readVarInt(), buf.readVarInt()));
    }
}
