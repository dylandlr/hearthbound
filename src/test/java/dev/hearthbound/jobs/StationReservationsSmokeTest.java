package dev.hearthbound.jobs;

import java.util.UUID;

/** Runnable without Minecraft or JUnit; models overlapping shared-stockpile requests. */
public final class StationReservationsSmokeTest {
    private static void check(boolean value) { if (!value) throw new AssertionError("Station reservation invariant"); }
    public static void main(String[] args) {
        var a = UUID.randomUUID(); var b = UUID.randomUUID(); var c = UUID.randomUUID();
        var ledger = new StationReservations();
        check(ledger.acquire(a, "a", 1, 2, 0));
        check(!ledger.acquire(b, "b", 2, 3, 1));
        check(ledger.holder(3) == null); // no partial acquisition
        check(!ledger.acquire(c, "c", 3, 4, 2)); // earlier overlapping waiter
        check(ledger.acquire(UUID.randomUUID(), "independent", 8, 9, 2));
        check(!ledger.release(a, "wrong-job"));
        check(ledger.acquire(a, "a", 1, 2, 100000)); // leases never time out
        check(!ledger.acquire(a, "other", 1, 2, 100000));
        check(ledger.release(a, "a"));
        // Renew B before C can pass; a fresh contender may not jump the queue.
        check(ledger.acquire(b, "b", 2, 3, 100001));
        check(!ledger.acquire(a, "next", 1, 2, 100002));
        check(ledger.release(b, "b"));
        check(ledger.acquire(a, "next", 1, 2, 100003));

        var saved = new StationReservations();
        for (var lease : ledger.leases()) saved.restore(lease);
        check(!saved.acquire(b, "after-restart", 2, 7, 999999));
        check(saved.lease(a).job().equals("next"));
        check(saved.release(a, "next"));
        check(saved.acquire(b, "after-restart", 2, 7, 999999));

        var pending = new StationReservations();
        check(pending.acquire(a, "hold", 1, 2, 0));
        check(!pending.acquire(b, "queued", 2, 3, 1));
        check(!pending.acquire(c, "later", 3, 4, 2));
        check(pending.release(a, "hold"));
        check(pending.acquire(c, "later", 3, 4, 123)); // abandoned request may expire
        check(pending.acquire(a, "hold-again", 1, 2, 123));
        check(!pending.acquire(b, "cancelled", 2, 5, 124));
        pending.cancelWaiting(b);
        check(pending.acquire(UUID.randomUUID(), "unblocked", 5, 6, 124));
        System.out.println("HB_STATION_RESERVATIONS_PASS atomic_pair queue_fairness safe_expiry restore exact_release");
    }
}
