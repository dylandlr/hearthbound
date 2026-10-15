package dev.hearthbound.jobs;

import java.util.UUID;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class WorkshopReservationsTest {
    @Test void sharedStationsQueueWithoutPartialLocksOrUnsafeLeaseExpiry() {
        StationReservationsSmokeTest.main(new String[0]);
    }
    @Test void onlyTheOwnerOrOperatorCanReuseAnOwnedMill() {
        var registry = new WorkshopRegistry();
        var mill = new BlockPos(-32, 100, 17);
        UUID owner = UUID.randomUUID(), stranger = UUID.randomUUID();
        assertEquals(owner, registry.claim(mill, owner, false));
        assertTrue(registry.canUse(mill, owner, false));
        assertFalse(registry.canUse(mill, stranger, false));
        assertThrows(IllegalStateException.class, () -> registry.claim(mill, stranger, false));
        assertEquals(owner, registry.claim(mill, stranger, true)); // operator never silently steals it
        assertFalse(registry.canUse(mill, null, false));
    }
    @Test void ownersAndBothLeaseEndpointsSurviveAnNbtRoundTrip() {
        UUID owner = UUID.randomUUID(), worker = UUID.randomUUID();
        var mill = new BlockPos(8, -60, 9);
        var registry = new WorkshopRegistry(); registry.claim(mill, owner, false);
        var tag = registry.save(new CompoundTag());
        var lease = new CompoundTag();
        lease.putUUID("Worker", worker); lease.putString("Job", "retained-cargo");
        lease.putLong("From", mill.asLong()); lease.putLong("To", new BlockPos(12, -60, 9).asLong());
        var leases = new ListTag(); leases.add(lease); tag.put("Leases", leases);
        var restored = WorkshopRegistry.load(tag);
        var twice = WorkshopRegistry.load(restored.save(new CompoundTag()));
        assertEquals(owner, twice.owner(mill));
        assertEquals("retained-cargo", twice.holder(mill).job());
        assertEquals(worker, twice.lease(worker).worker());
        assertEquals(lease.getLong("To"), twice.lease(worker).to());
        assertTrue(twice.wasRestored(worker, "retained-cargo"));
    }
    @Test void dimensionsKeepSeparateMachineOwners() {
        var first = new WorkshopRegistry(); var second = new WorkshopRegistry();
        var point = BlockPos.ZERO; UUID a = UUID.randomUUID(), b = UUID.randomUUID();
        first.claim(point, a, false); second.claim(point, b, false);
        assertEquals(a, first.owner(point)); assertEquals(b, second.owner(point));
    }
}
