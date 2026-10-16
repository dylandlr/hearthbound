package dev.hearthbound.research;

import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

final class CitizenTaskArbiterTest {
    @Test void conflictingTasksCannotAcquireSameCitizen() {
        CitizenTaskArbiter arbiter = new CitizenTaskArbiter();
        UUID citizen = UUID.randomUUID();
        arbiter.acquire(citizen, CitizenTaskArbiter.Kind.HAUL, 10);
        assertThrows(IllegalStateException.class,
                () -> arbiter.acquire(citizen, CitizenTaskArbiter.Kind.STUDY, 11));
    }
    @Test void staleReleaseDoesNotCancelNewAssignment() {
        CitizenTaskArbiter arbiter = new CitizenTaskArbiter();
        UUID citizen = UUID.randomUUID();
        var first = arbiter.acquire(citizen, CitizenTaskArbiter.Kind.STUDY, 10);
        assertTrue(arbiter.release(citizen, first.assignmentId()));
        var second = arbiter.acquire(citizen, CitizenTaskArbiter.Kind.HAUL, 11);
        assertFalse(arbiter.release(citizen, first.assignmentId()));
        assertEquals(second, arbiter.active(citizen));
    }
    @Test void restoreIsIdempotentButRejectsConflicts() {
        CitizenTaskArbiter arbiter = new CitizenTaskArbiter();
        UUID citizen = UUID.randomUUID();
        var lease = new CitizenTaskArbiter.Lease(UUID.randomUUID(),
                CitizenTaskArbiter.Kind.STUDY, 42);
        arbiter.restore(citizen, lease);
        arbiter.restore(citizen, lease);
        assertThrows(IllegalStateException.class, () ->
                arbiter.restore(citizen, new CitizenTaskArbiter.Lease(
                        UUID.randomUUID(), CitizenTaskArbiter.Kind.HAUL, 43)));
    }
}
