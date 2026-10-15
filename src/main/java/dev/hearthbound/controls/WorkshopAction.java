package dev.hearthbound.controls;

import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.network.FriendlyByteBuf;

/** Fixed bounded request. No client NBT or transferable items. */
public record WorkshopAction(UUID worker, int action, long revision, BlockPos wheat, BlockPos mill,
        BlockPos flour, BlockPos waiting, int target) {
    public static final int OPEN = 0, REFRESH = 1, SAVE = 2, STOP = 3, CLOSE = 4;
    public void encode(FriendlyByteBuf b) {
        b.writeUUID(worker); b.writeByte(action); b.writeLong(revision);
        point(b, wheat); point(b, mill); point(b, flour); point(b, waiting); b.writeInt(target);
    }
    public static WorkshopAction decode(FriendlyByteBuf b) {
        return new WorkshopAction(b.readUUID(), b.readUnsignedByte(), b.readLong(), point(b), point(b), point(b), point(b), b.readInt());
    }
    private static void point(FriendlyByteBuf b, BlockPos p) { b.writeBoolean(p != null); if (p != null) b.writeBlockPos(p); }
    private static BlockPos point(FriendlyByteBuf b) { return b.readBoolean() ? b.readBlockPos() : null; }
}
