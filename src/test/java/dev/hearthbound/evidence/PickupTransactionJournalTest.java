package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.file.*;
import java.util.UUID;

/** Standalone Java 17 crash-replay and corruption contract tests. */
public final class PickupTransactionJournalTest {
    private static void check(boolean value) { if (!value) throw new AssertionError(); }
    private static void fails(IoAction action) throws Exception {
        try { action.run(); throw new AssertionError("expected failure"); }
        catch (IOException | IllegalStateException expected) { /* fail closed */ }
    }
    @FunctionalInterface private interface IoAction { void run() throws Exception; }
    public static void main(String[] args) throws Exception {
        Path dir = Files.createTempDirectory("pickup-intent-test");
        Path file = dir.resolve("pickup.bin");
        UUID world = UUID.randomUUID(), actor = UUID.randomUUID();
        UUID failed = UUID.randomUUID(), interrupted = UUID.randomUUID(), cargo = UUID.randomUUID();
        var a = new PickupTransactionJournal.Intent(world, failed, actor, "overworld|1,2,3", "report-a", 10, 11);
        var b = new PickupTransactionJournal.Intent(world, interrupted, actor, "overworld|1,2,3", "report-b", 12, 13);
        var c = new PickupTransactionJournal.Intent(world, cargo, actor, "overworld|4,2,3", "report-c", 14, 15);
        try (var journal = new PickupTransactionJournal(file, world)) {
            journal.begin(a);
            journal.finish(failed, PickupTransactionJournal.State.EXTRACTION_EMPTY);
            journal.begin(b); // Simulated crash after fsync, before motor outcome.
            journal.begin(c);
            journal.finish(cargo, PickupTransactionJournal.State.CARGO_RETURNED);
            check(journal.unresolved().size() == 1);
            fails(() -> journal.begin(a));
            fails(() -> journal.finish(failed, PickupTransactionJournal.State.CARGO_RETURNED));
            fails(() -> journal.begin(new PickupTransactionJournal.Intent(
                UUID.randomUUID(), UUID.randomUUID(), actor, "source", "report", 1, 2)));
            fails(() -> new PickupTransactionJournal(file, world)); // Single writer.
        }
        try (var replay = new PickupTransactionJournal(file, world)) {
            check(replay.inspect(failed).state() == PickupTransactionJournal.State.EXTRACTION_EMPTY);
            check(replay.inspect(cargo).state() == PickupTransactionJournal.State.CARGO_RETURNED);
            check(replay.inspect(interrupted).requiresQuarantine());
            check(replay.unresolved().size() == 1);
            fails(() -> replay.begin(b));
        }
        fails(() -> new PickupTransactionJournal(file, UUID.randomUUID()));
        byte[] valid = Files.readAllBytes(file);
        Files.write(file, java.util.Arrays.copyOf(valid, valid.length - 1));
        fails(() -> new PickupTransactionJournal(file, world));
        Files.write(file, valid);
        byte[] tampered = valid.clone();
        tampered[valid.length - 10] ^= 0x04;
        Files.write(file, tampered);
        fails(() -> new PickupTransactionJournal(file, world));
        Files.write(file, valid);
        try (var restored = new PickupTransactionJournal(file, world)) {
            check(restored.unresolved().size() == 1);
        }
        System.out.println("PickupTransactionJournalTest passed");
    }
}
