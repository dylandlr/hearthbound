package dev.hearthbound.controls;

import dev.hearthbound.presentation.WorkerViewPacket;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;

/** Server-authored settings and public status, never an inventory. */
public record WorkshopSnapshot(WorkerViewPacket worker, String name, boolean canEdit, boolean busy,
        long revision, CompoundTag settings, String notice) {
    public void encode(FriendlyByteBuf b) {
        worker.encode(b); b.writeUtf(name, 128); b.writeBoolean(canEdit); b.writeBoolean(busy);
        b.writeLong(revision); b.writeNbt(settings); b.writeUtf(notice, 256);
    }
    public static WorkshopSnapshot decode(FriendlyByteBuf b) {
        var worker = WorkerViewPacket.decode(b); String name = b.readUtf(128);
        boolean edit = b.readBoolean(), busy = b.readBoolean(); long revision = b.readLong();
        var settings = b.readNbt();
        return new WorkshopSnapshot(worker, name, edit, busy, revision, settings == null ? new CompoundTag() : settings, b.readUtf(256));
    }
}
