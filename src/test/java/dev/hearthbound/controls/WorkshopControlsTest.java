package dev.hearthbound.controls;

import java.util.UUID;
import io.netty.buffer.Unpooled;
import net.minecraft.core.BlockPos;
import net.minecraft.network.FriendlyByteBuf;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class WorkshopControlsTest {
    @Test void onlyOwnerOrOperatorCanManageAnAssignedWorker() {
        UUID owner = UUID.randomUUID(), stranger = UUID.randomUUID();
        assertTrue(WorkshopAccess.canManage(owner, owner, false, false));
        assertFalse(WorkshopAccess.canManage(owner, stranger, false, true));
        assertTrue(WorkshopAccess.canManage(owner, stranger, true, false));
    }
    @Test void unownedBusyWorkersCannotBeClaimedByOpeningTheScreen() {
        UUID player = UUID.randomUUID();
        assertTrue(WorkshopAccess.canManage(null, player, false, true));
        assertFalse(WorkshopAccess.canManage(null, player, false, false));
    }
    @Test void fixedActionPayloadPreservesWorkerRevisionAndNegativeCoordinates() {
        var request = new WorkshopAction(UUID.randomUUID(), WorkshopAction.SAVE, 987L,
                new BlockPos(-32, -60, 17), BlockPos.ZERO, new BlockPos(3, 100, -1), null, 4096, UUID.randomUUID());
        var b = new FriendlyByteBuf(Unpooled.buffer());
        try {
            request.encode(b); assertTrue(b.readableBytes() <= 82);
            assertEquals(request, WorkshopAction.decode(b)); assertEquals(0, b.readableBytes());
        } finally { b.release(); }
    }
}
