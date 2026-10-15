package dev.hearthbound.controls;

import io.netty.buffer.Unpooled;
import java.util.UUID;
import dev.hearthbound.presentation.WorkerView;
import dev.hearthbound.presentation.WorkerViewPacket;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.FriendlyByteBuf;
import net.minecraft.resources.ResourceLocation;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class WorkshopStatusTest {
    private WorkshopStatus status() {
        return new WorkshopStatus("You", WorkshopStatus.Access.OWNER,
                new WorkshopStatus.Station(WorkshopStatus.State.FREE, new BlockPos(-32, -60, 17), "", 0, false, false),
                new WorkshopStatus.Station(WorkshopStatus.State.OTHER, BlockPos.ZERO, "Sable [shared a]", 2, true, true),
                new WorkshopStatus.Station(WorkshopStatus.State.AWAY, new BlockPos(3, 100, -1), "", 1, false, false));
    }
    @Test void stationInspectionRoundTripsExactPositionsQueueAndPausedHolder() {
        var original = status(); var b = new FriendlyByteBuf(Unpooled.buffer());
        try {
            original.encode(b); assertEquals(original, WorkshopStatus.decode(b)); assertEquals(0, b.readableBytes());
            assertTrue(b.writerIndex() < 512);
        } finally { b.release(); }
    }
    @Test void fullSnapshotPreservesSettingsAndWorkerIdentityAlongsidePublicStatus() {
        var worker = new WorkerViewPacket(72, UUID.randomUUID(), new ResourceLocation("minecraft", "overworld"),
                new WorkerView(true, "minecraft:wheat", 4, "paused", true, 0, 2));
        var settings = new CompoundTag(); settings.putLong("Mill", -928L); settings.putInt("TargetFlour", 2);
        var original = new WorkshopSnapshot(worker, "Sable", true, true, 19, settings, status(), "Current haul is paused.");
        var b = new FriendlyByteBuf(Unpooled.buffer());
        try {
            original.encode(b); assertEquals(original, WorkshopSnapshot.decode(b)); assertEquals(0, b.readableBytes());
        } finally { b.release(); }
    }
    @Test void publicLabelsAndQueueCountsAreBounded() {
        var empty = new WorkshopStatus.Station(WorkshopStatus.State.NONE, null, "", 0, false, false);
        assertThrows(IllegalArgumentException.class, () -> new WorkshopStatus("x".repeat(65), WorkshopStatus.Access.DENIED, empty, empty, empty));
        assertThrows(IllegalArgumentException.class, () -> new WorkshopStatus.Station(WorkshopStatus.State.OTHER, BlockPos.ZERO, "x".repeat(65), 0, false, false));
        assertThrows(IllegalArgumentException.class, () -> new WorkshopStatus.Station(WorkshopStatus.State.FREE, BlockPos.ZERO, "", -1, false, false));
        assertThrows(IllegalArgumentException.class, () -> new WorkshopStatus.Station(WorkshopStatus.State.FREE, BlockPos.ZERO, "", 1000, false, false));
    }
    @Test void statusExplainsTheHolderPauseAndWorkersOwnQueueMembership() {
        var mill = status().mill();
        assertTrue(mill.description().contains("Sable [shared a]"));
        assertTrue(mill.description().contains("paused"));
        assertTrue(mill.queueDescription().contains("2"));
        assertTrue(mill.queueDescription().contains("this worker is queued"));
        assertTrue(status().flour().description().contains("away"));
        var unavailable = new WorkshopStatus.Station(WorkshopStatus.State.UNAVAILABLE, BlockPos.ZERO, "", 0, false, false);
        assertFalse(unavailable.queueDescription().contains("Waiting: 0"));
    }
}
