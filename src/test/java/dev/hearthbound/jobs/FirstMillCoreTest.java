package dev.hearthbound.jobs;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** JUnit 5 behavior tests; run with ./gradlew test once Gradle wrapper/Forge is provisioned. */
class FirstMillCoreTest {
    @Test void transportHasExactlyOneWithdrawalAndDelivery() {
        TransferLedger t = new TransferLedger("x-1", "minecraft:wheat", 4);
        assertTrue(t.withdraw());
        assertFalse(t.withdraw());
        assertTrue(t.deliver());
        assertFalse(t.deliver());
        assertEquals(TransferLedger.Phase.DELIVERED, t.phase());
    }
    @Test void inFlightCargoCannotBeCancelled() {
        TransferLedger t = new TransferLedger("x-2", "minecraft:wheat", 4);
        assertTrue(t.withdraw());
        assertFalse(t.cancel());
        assertEquals(TransferLedger.Phase.WITHDRAWN, t.phase());
    }
    @Test void cannotDeliverBeforeWithdrawal() {
        TransferLedger t = new TransferLedger("x-3", "minecraft:wheat", 4);
        assertFalse(t.deliver());
        assertEquals(TransferLedger.Phase.PLANNED, t.phase());
    }
    @Test void recoveredCargoCanOnlyBeDeliveredOnce() {
        TransferLedger t = TransferLedger.restore("x-4", "minecraft:wheat", 4,
                TransferLedger.Phase.WITHDRAWN);
        assertTrue(t.deliver());
        assertFalse(t.deliver());
    }
    @Test void travelerEventuallyStopsWhenStuck() {
        TravelProgress p = new TravelProgress(0, 100);
        for (int i=1; i<10; i++)
            assertEquals(TravelProgress.Outcome.MOVING, p.sample(i*20, 100));
        assertEquals(TravelProgress.Outcome.STALLED, p.sample(200, 100));
    }
    @Test void timeoutStopsLongRunningTravel() {
        TravelProgress p = new TravelProgress(0, 100);
        assertEquals(TravelProgress.Outcome.TIMED_OUT, p.sample(1200, 100));
    }
    @Test void invalidSamplesRejected() {
        assertThrows(IllegalArgumentException.class, () -> new TravelProgress(0, -1));
        TravelProgress p = new TravelProgress(20, 9);
        assertThrows(IllegalArgumentException.class, () -> p.sample(19, 9));
    }
}
