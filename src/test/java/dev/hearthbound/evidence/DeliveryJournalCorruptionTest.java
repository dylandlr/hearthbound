package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.UUID;

/**
 * Regression: damaged delivery records must fail closed during startup.
 * A torn insertion-return must never be silently downgraded to a clean
 * finished delivery, nor be treated as automatic retry permission.
 */
public final class DeliveryJournalCorruptionTest {
    private static void check(boolean condition) {
        if (!condition) throw new AssertionError();
    }
    private static void rejects(Path path, UUID world) throws Exception {
        try (var ignored = new PickupTransactionJournal(path, world)) {
            throw new AssertionError("Corrupt delivery journal was accepted");
        } catch (IOException expected) {
            // Missing/truncated or hash-invalid frame must block writer startup.
        }
    }
    private static byte[] valid(UUID world, boolean finished) throws Exception {
        Path path = Files.createTempFile("hb-delivery-valid-", ".bin");
        UUID job = UUID.randomUUID(), actor = UUID.randomUUID();
        try (var journal = new PickupTransactionJournal(path, world)) {
            journal.begin(new PickupTransactionJournal.Intent(world, job, actor,
                "minecraft:overworld|3,101,1", "witness", 10, 11));
            journal.finish(job, PickupTransactionJournal.State.CARGO_RETURNED);
            journal.beginDelivery(new DeliveryBoundaryContract.Intent(
                world, job, actor, "minecraft:overworld|10,101,2", 12));
            if (finished) journal.finishDelivery(job);
        }
        return Files.readAllBytes(path);
    }
    public static void main(String[] args) throws Exception {
        UUID world = UUID.randomUUID();
        for (boolean finished : new boolean[] {false, true}) {
            byte[] original = valid(world, finished);
            Path intact = Files.createTempFile("hb-delivery-control-", ".bin");
            Files.write(intact, original);
            try (var journal = new PickupTransactionJournal(intact, world)) {
                check(journal.snapshot().size() == 1);
                check(journal.inspectDelivery(journal.snapshot().get(0).intent().job())
                    == (finished ? PickupTransactionJournal.DeliveryState.INSERTION_RETURNED
                        : PickupTransactionJournal.DeliveryState.INSERTION_UNRESOLVED));
            }
            // Detect all truncations into the last frame header or payload,
            // rather than treating an incomplete write as an absent outcome.
            for (int missing = 1; missing <= Math.min(12, original.length - 24); missing++) {
                Path torn = Files.createTempFile("hb-delivery-torn-", ".bin");
                Files.write(torn, java.util.Arrays.copyOf(original, original.length - missing));
                rejects(torn, world);
            }
            // A full-length frame with corrupted payload must fail CRC/hash.
            byte[] altered = original.clone();
            altered[altered.length - 1] ^= 0x01;
            Path corrupted = Files.createTempFile("hb-delivery-corrupt-", ".bin");
            Files.write(corrupted, altered);
            rejects(corrupted, world);
            // World identity always remains authoritative, even if frame CRCs
            // and the persisted delivery outcome are otherwise intact.
            Path foreign = Files.createTempFile("hb-delivery-foreign-", ".bin");
            Files.write(foreign, original);
            rejects(foreign, UUID.randomUUID());
        }
        System.out.println("DeliveryJournalCorruptionTest passed");
    }
}
