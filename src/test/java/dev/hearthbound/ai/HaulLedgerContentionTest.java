package dev.hearthbound.ai;

import static dev.hearthbound.ai.HaulLedger.State.*;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicReference;

/**
 * Deterministic acceptance invariants under genuinely concurrent callers.
 *
 * The scheduling order is deliberately unspecified; assert exactly one
 * winner for one shared source, not a chosen winning actor. This tests the
 * in-memory reservation ledger only, NOT real entity navigation or chests.
 */
public final class HaulLedgerContentionTest {
    private static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    private static void rejects(Runnable operation, String message) {
        try {
            operation.run();
            throw new AssertionError(message);
        } catch (IllegalStateException expected) {
            // Expected state-machine rejection, not success.
        }
    }

    private static void concurrentSingleSource() throws InterruptedException {
        final int contenders = 16;
        final HaulLedger ledger = new HaulLedger();
        final CountDownLatch ready = new CountDownLatch(contenders);
        final CountDownLatch start = new CountDownLatch(1);
        final CountDownLatch complete = new CountDownLatch(contenders);
        final AtomicInteger admitted = new AtomicInteger();
        final AtomicInteger denied = new AtomicInteger();
        final AtomicReference<Throwable> unexpected = new AtomicReference<>();
        final List<HaulLedger.Ticket> winners =
            java.util.Collections.synchronizedList(new ArrayList<>());
        for (int index = 0; index < contenders; index++) {
            final int citizen = index;
            Thread thread = new Thread(() -> {
                ready.countDown();
                try {
                    if (!start.await(5, TimeUnit.SECONDS))
                        throw new AssertionError("start barrier timed out");
                    try {
                        var ticket = ledger.reserve("citizen-" + citizen,
                            "shared-wheat-chest", "destination-" + citizen, 1);
                        winners.add(ticket);
                        admitted.incrementAndGet();
                    } catch (IllegalStateException reservationDenied) {
                        denied.incrementAndGet();
                    }
                } catch (Throwable error) {
                    unexpected.compareAndSet(null, error);
                } finally {
                    complete.countDown();
                }
            }, "haul-contender-" + index);
            thread.setDaemon(true);
            thread.start();
        }
        check(ready.await(10, TimeUnit.SECONDS), "all contenders ready");
        start.countDown();
        check(complete.await(10, TimeUnit.SECONDS), "all contenders finished");
        check(unexpected.get() == null, "unexpected worker failure " + unexpected.get());
        check(admitted.get() == 1, "exactly one reservation wins");
        check(denied.get() == contenders - 1, "all losing claims rejected");
        check(ledger.outstanding() == 1, "only one outstanding source claim");

        var first = winners.get(0);
        rejects(() -> ledger.reserve("intruder", "shared-wheat-chest", "other", 1),
                "reserved source must not be stolen");
        ledger.transition(first.id(), RESERVED, IN_TRANSIT);
        rejects(() -> ledger.transition(first.id(), RESERVED, CANCELLED),
                "stale cancellation must not release in-transit claim");
        rejects(() -> ledger.reserve("intruder", "shared-wheat-chest", "other", 1),
                "source remains locked while hauling");
        ledger.transition(first.id(), IN_TRANSIT, COMPLETE);
        check(ledger.outstanding() == 0, "completion releases shared source");

        var second = ledger.reserve("successor", "shared-wheat-chest", "new-target", 1);
        check(!second.id().equals(first.id()), "new claim has independent identity");
        ledger.transition(second.id(), RESERVED, CANCELLED);
        rejects(() -> ledger.transition(second.id(), RESERVED, CANCELLED),
                "duplicate cancellation cannot release twice");
        check(ledger.outstanding() == 0, "cancellation cleans up");
        var third = ledger.reserve("third", "shared-wheat-chest", "new-target", 1);
        check(third.state() == RESERVED, "source reusable after cancellation");
        ledger.transition(third.id(), RESERVED, CANCELLED);
    }

    private static void independentSources() throws InterruptedException {
        final int sources = 12;
        final HaulLedger ledger = new HaulLedger();
        CountDownLatch start = new CountDownLatch(1);
        CountDownLatch finished = new CountDownLatch(sources);
        AtomicReference<Throwable> exception = new AtomicReference<>();
        List<HaulLedger.Ticket> tickets =
            java.util.Collections.synchronizedList(new ArrayList<>());
        for (int index = 0; index < sources; index++) {
            final int source = index;
            new Thread(() -> {
                try {
                    if (!start.await(5, TimeUnit.SECONDS))
                        throw new AssertionError("source barrier timeout");
                    tickets.add(ledger.reserve("citizen-" + source,
                        "chest-" + source, "common-granary", 1));
                } catch (Throwable error) {
                    exception.compareAndSet(null, error);
                } finally {
                    finished.countDown();
                }
            }, "independent-chest-" + index).start();
        }
        start.countDown();
        check(finished.await(10, TimeUnit.SECONDS), "parallel reservations ended");
        check(exception.get() == null, "parallel source contention " + exception.get());
        check(tickets.size() == sources, "different sources independently reserved");
        check(ledger.outstanding() == sources, "all distinct claims outstanding");
        Set<java.util.UUID> identities = new HashSet<>();
        for (var ticket : tickets) {
            check(identities.add(ticket.id()), "unique job identity");
            ledger.transition(ticket.id(), RESERVED, IN_TRANSIT);
            ledger.transition(ticket.id(), IN_TRANSIT, COMPLETE);
        }
        check(ledger.outstanding() == 0, "all independent claims released");
    }

    private static void conservationBoundary() {
        final HaulLedger ledger = new HaulLedger();
        var reserved = ledger.reserve("sable", "source", "destination", 1);
        check(reserved.units() == 1, "ticket units remain explicit");
        rejects(() -> ledger.reserve("iven", "source", "second", 2),
                "claim collision denied even with different quantity");
        check(ledger.outstanding() == 1, "failed reservation is not a ticket");
        ledger.transition(reserved.id(), RESERVED, CANCELLED);
        check(ledger.get(reserved.id()).state() == CANCELLED,
              "cancellation retains terminal receipt");
        check(ledger.outstanding() == 0, "no abandoned claims");
    }

    public static void main(String[] args) throws Exception {
        for (int repetition = 0; repetition < 20; repetition++)
            concurrentSingleSource();
        independentSources();
        conservationBoundary();
        System.out.println("HAUL_LEDGER_CONCURRENT_CONTENTION_PASS rounds=20 citizens=16 independent_sources=12");
    }
}
