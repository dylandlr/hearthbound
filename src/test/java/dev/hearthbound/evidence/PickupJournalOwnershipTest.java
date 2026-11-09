package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;

/** Standalone Java 17 ownership and restart tests. */
public final class PickupJournalOwnershipTest {
    @FunctionalInterface interface Action { void run() throws Exception; }
    static void check(boolean test) { if (!test) throw new AssertionError(); }
    static void denied(Action action) throws Exception {
        try { action.run(); throw new AssertionError("expected fail-closed denial"); }
        catch (IOException expected) { }
    }
    public static void main(String[] args) throws Exception {
        UUID world = UUID.randomUUID();
        Path folder = Files.createTempDirectory("pickup-world-owner");
        try (PickupTransactionJournal first = PickupJournalOwnership.open(folder, world)) {
            check(first.unresolved().isEmpty());
            denied(() -> PickupJournalOwnership.open(folder, world));
        }
        Path marker = folder.resolve(PickupJournalOwnership.MARKER);
        Path journal = folder.resolve(PickupJournalOwnership.JOURNAL);
        check(Files.isRegularFile(marker) && Files.isRegularFile(journal));
        try (PickupTransactionJournal restarted = PickupJournalOwnership.open(folder, world)) {
            check(restarted.unresolved().isEmpty());
        }
        denied(() -> PickupJournalOwnership.open(folder, UUID.randomUUID()));
        byte[] originalMarker = Files.readAllBytes(marker);
        Files.delete(journal);
        denied(() -> PickupJournalOwnership.open(folder, world));
        Files.delete(marker);
        try (PickupTransactionJournal initialized = PickupJournalOwnership.open(folder, world)) {
            check(initialized.unresolved().isEmpty());
        }
        Files.delete(marker);
        denied(() -> PickupJournalOwnership.open(folder, world));
        Files.write(marker, originalMarker);
        Files.writeString(marker, "incorrect owner");
        denied(() -> PickupJournalOwnership.open(folder, world));
        Files.write(marker, originalMarker);
        byte[] originalJournal = Files.readAllBytes(journal);
        Files.write(journal, java.util.Arrays.copyOf(originalJournal, 3));
        denied(() -> PickupJournalOwnership.open(folder, world));
        Files.write(journal, originalJournal);
        try (PickupTransactionJournal repairedTestFixture = PickupJournalOwnership.open(folder, world)) {
            check(repairedTestFixture.unresolved().isEmpty());
        }
        System.out.println("PickupJournalOwnershipTest passed");
    }
}
