package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.UUID;
import java.util.zip.CRC32;

/** Java 17 standalone tests. These NEVER simulate credit delivery or real Minecraft. */
public final class CausalEvidenceJournalTest {
    private static int checks;
    private static void yes(boolean condition) {
        checks++;
        if (!condition) throw new AssertionError("failed journal check #" + checks);
    }
    private static void rejects(Throwing action) {
        boolean failed = false;
        try { action.run(); }
        catch (Exception expected) { failed = true; }
        yes(failed);
    }
    @FunctionalInterface private interface Throwing { void run() throws Exception; }

    private static CausalEvidenceJournal.Observation observed(
            UUID world, String job, String citizen, long machine, long assigned,
            long start, long finish) {
        String dimension = "minecraft:overworld";
        String event = "hearthbound:mill:v1:" + world + ":" + dimension + ":" + job;
        String physical = "hearthbound:create-process:v1:" + world + ":"
            + dimension + ":" + machine + ":" + job + ":" + start + ":" + finish;
        return new CausalEvidenceJournal.Observation(world, event, physical, job, citizen,
            dimension, machine, assigned, start, finish);
    }

    private static void crcOnFrame(byte[] bytes, int at) {
        int length = ByteBuffer.wrap(bytes, at, 4).getInt();
        CRC32 crc = new CRC32();
        crc.update(bytes, at + 8, length);
        ByteBuffer.wrap(bytes, at + 4, 4).putInt((int) crc.getValue());
    }

    public static void main(String[] args) throws Exception {
        Path root = Files.createTempDirectory("hearthbound-causal-evidence-");
        UUID world = UUID.randomUUID();
        String job = UUID.randomUUID().toString();
        String citizen = UUID.randomUUID().toString();
        var evidence = observed(world, job, citizen, 41024212, 8, 25, 49);
        Path primary = root.resolve("main.bin");

        // Initial source admission is an AUDIT status, not a durable reward.
        try (var journal = new CausalEvidenceJournal(primary, world)) {
            yes(journal.size() == 0);
            yes(journal.inspect(evidence.eventId()) == null);
            yes(journal.observe(evidence));
            yes(!journal.observe(evidence));
            yes(journal.size() == 1);
            yes(journal.inspect(evidence.eventId()).state()
                == CausalEvidenceJournal.State.OBSERVED);
            yes(!journal.inspect(evidence.eventId()).activeForAudit());
            rejects(() -> journal.observe(new CausalEvidenceJournal.Observation(
                world, evidence.eventId(), evidence.physicalEvidenceId(), job,
                UUID.randomUUID().toString(), evidence.dimension(), evidence.machinePos(),
                evidence.assignedTick(), evidence.startTick(), evidence.finishTick())));
            var admitted = journal.reconcile(evidence.eventId(), candidate -> {
                yes(candidate.equals(evidence));
                return true;
            });
            yes(admitted.state() == CausalEvidenceJournal.State.ADMITTED);
            yes(admitted.activeForAudit());
            long beforeReplay = Files.size(primary);
            var replay = journal.reconcile(evidence.eventId(), candidate -> true);
            yes(replay.activeForAudit());
            yes(Files.size(primary) == beforeReplay);
            rejects(() -> new CausalEvidenceJournal(primary, world)); // exclusive lock
            rejects(() -> journal.observe(observed(UUID.randomUUID(),job,citizen,1,1,2,3)));
        }
        // Persisted ADMITTED is never a valid post-restart authority by itself.
        try (var journal = new CausalEvidenceJournal(primary, world)) {
            var recovered = journal.inspect(evidence.eventId());
            yes(recovered.state() == CausalEvidenceJournal.State.ADMITTED);
            yes(!recovered.revalidatedThisSession());
            yes(!recovered.activeForAudit());
            yes(!journal.observe(evidence));
            yes(journal.reconcile(evidence.eventId(), e -> true).activeForAudit());
            yes(journal.inspect(evidence.eventId()).activeForAudit());
        }
        // After a second fresh reboot, late source mismatch is irreversible.
        try (var journal = new CausalEvidenceJournal(primary, world)) {
            yes(!journal.inspect(evidence.eventId()).activeForAudit());
            var revoked = journal.reconcile(evidence.eventId(), e -> false);
            yes(revoked.state() == CausalEvidenceJournal.State.REVOKED);
            yes(!revoked.activeForAudit());
            yes("SOURCE_MISMATCH_OR_TAINT".equals(revoked.revocationReason()));
            yes(!journal.revoke(evidence.eventId(), "SECOND_REASON"));
            yes(journal.inspect(evidence.eventId()).state()
                == CausalEvidenceJournal.State.REVOKED);
            rejects(() -> journal.reconcile("unknown", e -> true));
        }
        try (var journal = new CausalEvidenceJournal(primary, world)) {
            yes(journal.inspect(evidence.eventId()).state()
                == CausalEvidenceJournal.State.REVOKED);
            yes(!journal.reconcile(evidence.eventId(), e -> true).activeForAudit());
            yes(!journal.observe(evidence)); // terminal, never erased or promoted
            yes(journal.size() == 1);
        }
        rejects(() -> new CausalEvidenceJournal(primary, UUID.randomUUID()));
        rejects(() -> observed(world,job,citizen,100,50,40,60));
        rejects(() -> observed(world,job,citizen,100,10,40,40));
        rejects(() -> new CausalEvidenceJournal.Observation(world,
            "forged-event",evidence.physicalEvidenceId(),job,citizen,"minecraft:overworld",
            41024212,8,25,49));
        rejects(() -> new CausalEvidenceJournal.Observation(world,
            evidence.eventId(),"forged-physical",job,citizen,"minecraft:overworld",
            41024212,8,25,49));

        // A failed live verifier must NOT permit recovery to silently retain
        // an earlier process-local authorization. An exception also fails closed.
        Path transientFile = root.resolve("source-error.bin");
        var other = observed(world, UUID.randomUUID().toString(), citizen, 56,1,2,3);
        try (var journal = new CausalEvidenceJournal(transientFile, world)) {
            journal.observe(other);
            rejects(() -> journal.reconcile(other.eventId(), e -> {
                throw new IOException("machine chunk unavailable");
            }));
            yes(!journal.inspect(other.eventId()).activeForAudit());
            yes(journal.inspect(other.eventId()).state()
                == CausalEvidenceJournal.State.OBSERVED);
            yes(journal.reconcile(other.eventId(), e -> true).activeForAudit());
            yes(journal.revoke(other.eventId(), "OPERATOR_REVOKED"));
            yes(!journal.inspect(other.eventId()).activeForAudit());
        }
        try (var journal = new CausalEvidenceJournal(transientFile, world)) {
            yes("OPERATOR_REVOKED".equals(journal.inspect(other.eventId()).revocationReason()));
        }

        // Invalid framing, wrong world identity and corruption must not be
        // salvaged into a new trusted state.
        byte[] original = Files.readAllBytes(primary);
        Path corrupt = root.resolve("corrupt.bin");
        byte[] altered = original.clone();
        altered[original.length - 2] ^= 0x23;
        Files.write(corrupt, altered);
        rejects(() -> new CausalEvidenceJournal(corrupt, world));
        byte[] badHeader = original.clone();
        badHeader[8] ^= 0x4;
        Files.write(corrupt, badHeader);
        rejects(() -> new CausalEvidenceJournal(corrupt, world));
        Files.write(corrupt, Arrays.copyOf(original, original.length - 1));
        rejects(() -> new CausalEvidenceJournal(corrupt, world));
        Files.write(corrupt, Arrays.copyOf(original, 7));
        rejects(() -> new CausalEvidenceJournal(corrupt, world));

        // Recompute the CRC of a forged first-frame sequence: the separate
        // monotonic sequence + SHA-256 chain must reject it.
        byte[] fakeSequence = original.clone();
        int at = 28;
        fakeSequence[at + 8 + 7] ^= 0x04; // first payload sequence 1 -> 5
        crcOnFrame(fakeSequence, at);
        Files.write(corrupt, fakeSequence);
        rejects(() -> new CausalEvidenceJournal(corrupt, world));

        // A foreign UUID must be rejected even if the file has a clean header
        // and every payload checksum is valid.
        Path otherWorld = root.resolve("isolated.bin");
        try (var journal = new CausalEvidenceJournal(otherWorld, UUID.randomUUID())) {
            yes(journal.size() == 0);
        }
        rejects(() -> new CausalEvidenceJournal(otherWorld, world));

        System.out.println("CausalEvidenceJournalTest: " + checks
            + " checks passed (audit-only; no rewards or model updates)");
    }
}
