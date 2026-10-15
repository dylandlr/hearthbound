package dev.hearthbound.controls;

import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.network.FriendlyByteBuf;

/** Fixed bounded request. No client NBT, names, or transferable items. */
public record WorkshopAction(UUID worker, int action, long revision, BlockPos wheat, BlockPos mill,
        BlockPos flour, BlockPos waiting, int target, UUID player) {
    public static final int OPEN = 0, REFRESH = 1, SAVE = 2, STOP = 3, CLOSE = 4, RESUME = 5,
            SHARE = 6, REVOKE = 7, RELEASE = 8;
    public void encode(FriendlyByteBuf b) {
        b.writeUUID(worker); b.writeByte(action); b.writeLong(revision);
        point(b, wheat); point(b, mill); point(b, flour); point(b, waiting); b.writeInt(target);
        b.writeBoolean(player != null); if (player != null) b.writeUUID(player);
    }
    public static WorkshopAction decode(FriendlyByteBuf b) {
        UUID worker = b.readUUID(); int action = b.readUnsignedByte(); long revision = b.readLong();
        BlockPos wheat = point(b), mill = point(b), flour = point(b), waiting = point(b); int target = b.readInt();
        return new WorkshopAction(worker, action, revision, wheat, mill, flour, waiting, target,
                b.readBoolean() ? b.readUUID() : null);
    }
    private static void point(FriendlyByteBuf b, BlockPos p) { b.writeBoolean(p != null); if (p != null) b.writeBlockPos(p); }
    private static BlockPos point(FriendlyByteBuf b) { return b.readBoolean() ? b.readBlockPos() : null; }
}
