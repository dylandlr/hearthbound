package dev.hearthbound.civilization;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import dev.hearthbound.civilization.NeedServiceKernel.*;

/** Standalone contracts; physical sensor/motor authenticity is tested in Forge. */
public final class NeedServiceKernelTest {
    static UUID id(String name) { return UUID.nameUUIDFromBytes(name.getBytes(StandardCharsets.UTF_8)); }
    static void check(boolean value) { if (!value) throw new AssertionError(); }
    static void reject(Runnable work) {
        try { work.run(); } catch (IllegalArgumentException | IllegalStateException expected) { return; }
        throw new AssertionError("Expected rejection");
    }
    static final Scope SCOPE = new Scope(id("world"), "minecraft:overworld");
    static final UUID A = id("a"), B = id("b"), C = id("c"), NEED = id("need");
    static Need need(int units, long revision, UUID observer, long tick) {
        return new Need(NEED, SCOPE, 100, "minecraft:wheat", units, revision, observer, tick, tick + 600);
    }
    static NeedServiceKernel ready(int units) {
        var kernel = new NeedServiceKernel(SCOPE);
        kernel.observe(need(units, 1, A, 0), 0);
        kernel.receive(kernel.packet(A, B, NEED, 1), 1);
        kernel.receive(kernel.packet(A, C, NEED, 1), 1);
        return kernel;
    }
    static TransferReceipt receipt(Commitment c, long tick) {
        return new TransferReceipt(id("receipt:" + c.id()), SCOPE, c.id(), c.citizen(), c.job(), 100, tick, 1);
    }
    static void privateEvidenceAndTransport() {
        var kernel = new NeedServiceKernel(SCOPE);
        check(kernel.observe(need(2, 1, A, 0), 0));
        check(kernel.known(B, 0).isEmpty());
        check(kernel.reserve(B, NEED, 1, 1, 100) == null);
        Packet p = kernel.packet(A, B, NEED, 1);
        check(p.equals(kernel.packet(A, B, NEED, 2)));
        check(kernel.receive(p, 3));
        check(!kernel.receive(p, 4));
        Knowledge k = kernel.known(B, 4).get(0);
        check(!k.direct() && k.need().observedTick() == 0 && k.learnedTick() == 3);
        Packet forwarded = kernel.packet(B, C, NEED, 5);
        check(forwarded.parent().equals(p.id()) && forwarded.hops() == 2);
        check(forwarded.need().equals(p.need()));
        check(kernel.receive(forwarded, 6));
        check(kernel.known(C, 601).isEmpty());
        check(kernel.packet(C, A, NEED, 601) == null);
        reject(() -> kernel.receive(new Packet(id("forged"), p.need(), A, B, 1, 1, null), 7));
        check(kernel.observe(need(0, 2, A, 8), 8));
        check(kernel.known(B, 8).get(0).need().units() == 2); // No shared-board leak.
        check(kernel.reserve(B, NEED, 1, 8, 100) == null); // Execution arbitration refuses closed demand.
        check(kernel.receive(kernel.packet(A, B, NEED, 8), 8));
        check(kernel.known(B, 8).get(0).need().units() == 0);
    }
    static void exactQuantitySurvivesRefresh() {
        var kernel = ready(2);
        Commitment a = kernel.reserve(A, NEED, 1, 2, 100);
        check(a != null && kernel.availableUnits(NEED, 2) == 1);
        check(kernel.observe(need(2, 2, A, 3), 3));
        check(kernel.availableUnits(NEED, 3) == 1);
        Commitment b = kernel.reserve(B, NEED, 1, 3, 100); // Old private positive request remains useful.
        check(b != null && kernel.availableUnits(NEED, 3) == 0);
        check(kernel.reserve(C, NEED, 1, 3, 100) == null);
        check(kernel.reserve(B, NEED, 1, 3, 100) == null);
        kernel.begin(a.id(), A, id("a-job"), 4);
        check(!kernel.shouldCancel(a.id(), 4));
        check(kernel.observe(need(2, 3, A, 5), 5));
        check(!kernel.shouldCancel(a.id(), 5));
        check(kernel.availableUnits(NEED, 5) == 0);
        kernel.cancelBeforePickup(b.id(), B, null, 6);
        check(kernel.availableUnits(NEED, 6) == 1);
        check(kernel.reserve(C, NEED, 1, 6, 100) != null);
    }
    static void closureNeverDeletesCargoOrJobs() {
        var kernel = ready(2);
        Commitment a = kernel.reserve(A, NEED, 1, 2, 100);
        Commitment b = kernel.reserve(B, NEED, 1, 2, 100);
        a = kernel.begin(a.id(), A, id("a-running"), 3);
        b = kernel.begin(b.id(), B, id("b-running"), 3);
        kernel.pickedUp(b.id(), b.job(), 4);
        kernel.observe(need(0, 2, C, 5), 5);
        check(kernel.shouldCancel(a.id(), 5));
        kernel.expire(5);
        check(kernel.active(A).state() == State.RUNNING);
        check(kernel.active(B).state() == State.DRAINING);
        Commitment finalB = b;
        reject(() -> kernel.cancelBeforePickup(finalB.id(), B, finalB.job(), 6));
        kernel.cancelBeforePickup(a.id(), A, a.job(), 6);
        check(kernel.active(A) == null);
        check(kernel.delivered(receipt(b, 7)));
        check(!kernel.delivered(receipt(b, 7)));
        check(kernel.active(B) == null && kernel.availableUnits(NEED, 7) == 0);
        reject(() -> kernel.delivered(new TransferReceipt(id("replayed-differently"), SCOPE,
            finalB.id(), B, finalB.job(), 100, 8, 1)));
    }
    static void delayedAndSameTickReceiptOrdering() {
        var delayed = ready(2);
        Commitment c = delayed.reserve(B, NEED, 1, 2, 100);
        c = delayed.begin(c.id(), B, id("delay-job"), 3);
        delayed.observe(need(1, 2, A, 30), 30); // This physical shortfall already includes the insertion at20.
        check(delayed.delivered(receipt(c, 20)));
        check(delayed.availableUnits(NEED, 30) == 1);
        var ambiguous = ready(2);
        Commitment other = ambiguous.reserve(B, NEED, 1, 2, 100);
        other = ambiguous.begin(other.id(), B, id("same-tick-job"), 3);
        ambiguous.observe(need(1, 2, A, 20), 20);
        ambiguous.delivered(receipt(other, 20));
        check(ambiguous.availableUnits(NEED, 20) == 0);
        ambiguous.observe(need(1, 3, A, 20), 20);
        check(ambiguous.availableUnits(NEED, 20) == 0);
        ambiguous.observe(need(1, 4, A, 21), 21);
        check(ambiguous.availableUnits(NEED, 21) == 1);
    }
    static void expiryRestartAndPersistence() {
        var kernel = ready(2);
        Commitment waiting = kernel.reserve(A, NEED, 1, 2, 10);
        Commitment running = kernel.reserve(B, NEED, 1, 2, 10);
        running = kernel.begin(running.id(), B, id("restart-job"), 3);
        kernel.expire(11);
        check(kernel.commitment(waiting.id()).state() == State.CANCELLED);
        check(kernel.commitment(running.id()).state() == State.RUNNING);
        var snapshot = kernel.snapshot();
        var restored = NeedServiceKernel.restore(snapshot, SCOPE, 12);
        check(restored.active(B).state() == State.HELD);
        restored.expire(700);
        check(restored.active(B).state() == State.HELD);
        check(restored.known(B, 700).isEmpty());
        check(restored.delivered(receipt(running, 13)));
        var settled = restored.snapshot();
        check(NeedServiceKernel.restore(settled, SCOPE, 700).snapshot().equals(settled));
        reject(() -> NeedServiceKernel.restore(snapshot, new Scope(id("wrong-world"), "minecraft:overworld"), 12));
        reject(() -> NeedServiceKernel.restore(snapshot, SCOPE, 1));
        var missingReceipts = new Snapshot(snapshot.schemaVersion(), snapshot.scope(), snapshot.needs(),
            snapshot.books(), snapshot.packets(), List.of(), snapshot.commitments(), snapshot.transfers());
        reject(() -> NeedServiceKernel.restore(missingReceipts, SCOPE, 12));
        var changedBooks = new ArrayList<>(snapshot.books());
        changedBooks.set(0, new BookEntry(A, new Knowledge(need(1, 1, A, 0), null, A, 0, 0)));
        var conflict = new Snapshot(snapshot.schemaVersion(), snapshot.scope(), snapshot.needs(), changedBooks,
            snapshot.packets(), snapshot.receivedPackets(), snapshot.commitments(), snapshot.transfers());
        reject(() -> NeedServiceKernel.restore(conflict, SCOPE, 12));
    }
    static void productiveCustodyAndActualYield() {
        var kernel = new NeedServiceKernel(SCOPE);
        kernel.observe(new Need(NEED, SCOPE, 100, "create:wheat_flour", 3, 1, A, 0, 600), 0);
        Commitment c = kernel.reserve(A, NEED, 1, 1, 20);
        c = kernel.begin(c.id(), A, id("flour-input-job"), 2);
        kernel.pickedUp(c.id(), c.job(), 3);
        check(kernel.availableUnits(NEED, 3) == 2);
        c = kernel.beginProcessing(c.id(), c.job(), 4);
        check(c.state() == State.PROCESSING && kernel.snapshot().transfers().isEmpty());
        check(kernel.availableUnits(NEED, 4) == 2); // Input insertion does not fulfill flour demand.
        check(kernel.beginProcessing(c.id(), c.job(), 5).equals(c));
        Commitment processing = c;
        reject(() -> kernel.cancelBeforePickup(processing.id(), A, processing.job(), 6));
        reject(() -> kernel.beginProcessing(processing.id(), id("foreign-job"), 6));
        kernel.observe(new Need(NEED, SCOPE, 100, "create:wheat_flour", 3, 2, A, 10, 610), 10);
        check(kernel.availableUnits(NEED, 10) == 2); // Fresh observation retains the pending batch.
        kernel.expire(21);
        check(kernel.active(A).state() == State.PROCESSING);
        var restored = NeedServiceKernel.restore(kernel.snapshot(), SCOPE, 22);
        check(restored.active(A).state() == State.HELD);
        check(restored.availableUnits(NEED, 22) == 2);
        kernel.observe(new Need(NEED, SCOPE, 100, "create:wheat_flour", 0, 3, A, 23, 623), 23);
        kernel.expire(24);
        check(kernel.active(A).state() == State.PROCESSING); // Closure cannot abandon machine custody.
        var output = new TransferReceipt(id("physical-flour-output"), SCOPE, c.id(), A, c.job(), 100, 30, 4);
        var beforeFinal = restored.snapshot();
        restored.validateDelivery(output);
        check(restored.snapshot().equals(beforeFinal));
        reject(() -> restored.validateDelivery(new TransferReceipt(id("wrong-output-site"), SCOPE,
            processing.id(), A, processing.job(), 200, 30, 4)));
        check(restored.delivered(output)); // Actual yield, including surplus, is preserved.
        check(!restored.delivered(output));
        check(restored.active(A) == null && restored.availableUnits(NEED, 30) == 0);
        check(restored.snapshot().needs().get(0).deliveredSinceObservation() == 4);
        check(NeedServiceKernel.restore(restored.snapshot(), SCOPE, 30).snapshot().equals(restored.snapshot()));
        reject(() -> restored.delivered(new TransferReceipt(id("different-output-id"), SCOPE,
            processing.id(), A, processing.job(), 100, 31, 4)));
        var old = ready(1).snapshot();
        var legacy = new Snapshot(1, old.scope(), old.needs(), old.books(), old.packets(), old.receivedPackets(),
            old.commitments(), old.transfers());
        check(NeedServiceKernel.restore(legacy, SCOPE, 2).snapshot().schemaVersion() == NeedServiceKernel.SCHEMA_VERSION);
        reject(() -> new Snapshot(1, kernel.scope(), kernel.snapshot().needs(), kernel.snapshot().books(),
            kernel.snapshot().packets(), kernel.snapshot().receivedPackets(), kernel.snapshot().commitments(), List.of()));
    }
    public static void main(String[] args) {
        privateEvidenceAndTransport(); exactQuantitySurvivesRefresh(); closureNeverDeletesCargoOrJobs();
        delayedAndSameTickReceiptOrdering(); expiryRestartAndPersistence(); productiveCustodyAndActualYield();
        System.out.println("Need service kernel: PASS (private requests, batch claims, processing custody, actual output, restart)");
    }
}
