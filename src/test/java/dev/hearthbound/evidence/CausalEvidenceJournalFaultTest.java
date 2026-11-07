package dev.hearthbound.evidence;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import java.util.zip.CRC32;

/**
 * Adversarial crash/rollback acceptance for the offline journal contract.
 * This does not model a Forge world; real rollback is tested independently.
 * In particular, passing these tests NEVER authorizes a research payout.
 */
public final class CausalEvidenceJournalFaultTest {
    private static int checks;
    private static void yes(boolean ok) {
        checks++;
        if (!ok) throw new AssertionError("fault acceptance check " + checks);
    }
    @FunctionalInterface private interface Action { void perform() throws Exception; }
    private static void rejects(Action action) {
        boolean rejected = false;
        try { action.perform(); } catch (Exception expected) { rejected = true; }
        yes(rejected);
    }
    private static CausalEvidenceJournal.Observation observation(UUID world, UUID job, UUID citizen,
            long machine, long assignedTick, long start, long finish) {
        String dimension = "minecraft:overworld";
        String id = "hearthbound:mill:v1:" + world + ":" + dimension + ":" + job;
        String physical = "hearthbound:create-process:v1:" + world + ":"
            + dimension + ":" + machine + ":" + job + ":" + start + ":" + finish;
        return new CausalEvidenceJournal.Observation(world, id, physical, job.toString(),
            citizen.toString(), dimension, machine, assignedTick, start, finish);
    }

    private static List<Integer> frameEnds(byte[] all) {
        List<Integer> ends = new ArrayList<>();
        ends.add(28); // HBCJ versioned world-UUID header
        int pos = 28;
        while (pos < all.length) {
            if (pos + 8 > all.length) throw new AssertionError("bad test fixture frame");
            int size = ByteBuffer.wrap(all, pos, 4).getInt();
            if (size <= 0 || pos + 8 + size > all.length)
                throw new AssertionError("bad test fixture payload");
            pos += 8 + size;
            ends.add(pos);
        }
        return ends;
    }

    private static void rewriteCrc(byte[] payload, int pos) {
        int len = ByteBuffer.wrap(payload, pos, 4).getInt();
        CRC32 crc = new CRC32();
        crc.update(payload, pos + 8, len);
        ByteBuffer.wrap(payload, pos + 4, 4).putInt((int) crc.getValue());
    }

    public static void main(String[] args) throws Exception {
        Path folder = Files.createTempDirectory("hearthbound-causal-fault-injection-");
        Path valid = folder.resolve("valid.bin");
        UUID world = UUID.randomUUID(), citizen = UUID.randomUUID();
        var a = observation(world, UUID.randomUUID(), citizen, 512L, 15, 30, 56);
        var b = observation(world, UUID.randomUUID(), citizen, 513L, 60, 80, 93);

        try (var journal = new CausalEvidenceJournal(valid, world)) {
            yes(journal.observe(a));
            yes(journal.reconcile(a.eventId(), receipt -> true).activeForAudit());
            yes(journal.observe(b));
            yes(journal.reconcile(b.eventId(), receipt -> true).activeForAudit());
            yes(journal.revoke(b.eventId(), "OPERATOR_INVALIDATED"));
            yes(!journal.inspect(b.eventId()).activeForAudit());
            yes(journal.inspect(a.eventId()).activeForAudit());
        }
        byte[] whole = Files.readAllBytes(valid);
        List<Integer> boundaries = frameEnds(whole);
        yes(boundaries.size() == 6); // 5 records plus header
        yes(boundaries.get(boundaries.size() - 1) == whole.length);

        // Simulate every possible crash point. Any partially written header,
        // checksum, or payload must be rejected (never truncated/repaired).
        // A fully aligned prefix is structurally valid; its recovered ADMITTED
        // entries must still be inactive until revalidated against Minecraft.
        for (int truncatedAt = 1; truncatedAt < whole.length; truncatedAt++) {
            final int cut = truncatedAt;
            Path target = folder.resolve("partial-" + cut + ".bin");
            Files.write(target, Arrays.copyOf(whole, cut));
            if (boundaries.contains(cut)) {
                try (var journal = new CausalEvidenceJournal(target, world)) {
                    var first = journal.inspect(a.eventId());
                    var second = journal.inspect(b.eventId());
                    if (first != null) yes(!first.activeForAudit());
                    if (second != null) yes(!second.activeForAudit());
                    yes(journal.size() <= 2);
                }
            } else {
                rejects(() -> new CausalEvidenceJournal(target, world));
            }
            Files.deleteIfExists(target);
        }

        // The header+OBSERVE+ADMIT prefix is valid, but no previous admission
        // can survive reopening without an independent current-source check.
        Path oldCheckpoint = folder.resolve("old-checkpoint.bin");
        int priorAdmission = boundaries.get(2);
        Files.write(oldCheckpoint, Arrays.copyOf(whole, priorAdmission));
        try (var journal = new CausalEvidenceJournal(oldCheckpoint, world)) {
            yes(journal.inspect(a.eventId()).state() == CausalEvidenceJournal.State.ADMITTED);
            yes(!journal.inspect(a.eventId()).activeForAudit());
            // Simulated rollback of the source Minecraft SavedData or NBT:
            // the append-only evidence log may be ahead of the world.
            var revoked = journal.reconcile(a.eventId(), evidence -> false);
            yes(revoked.state() == CausalEvidenceJournal.State.REVOKED);
            yes(!revoked.activeForAudit());
        }
        try (var journal = new CausalEvidenceJournal(oldCheckpoint, world)) {
            yes(journal.inspect(a.eventId()).state() == CausalEvidenceJournal.State.REVOKED);
            yes(!journal.reconcile(a.eventId(), evidence -> true).activeForAudit());
        }

        // Alter only the observed citizen UUID, which is NOT part of the
        // event/physical ID canonicality check. Recompute the frame CRC to
        // ensure it is specifically the NEXT frame's SHA-256 parent digest
        // (not another validation rule) that detects the modification.
        byte[] forged = whole.clone();
        byte[] citizenBytes = citizen.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8);
        int changed = -1;
        for (int offset = 36; offset + citizenBytes.length <= boundaries.get(1); offset++) {
            boolean matches = true;
            for (int i = 0; i < citizenBytes.length; i++) {
                if (forged[offset + i] != citizenBytes[i]) {
                    matches = false;
                    break;
                }
            }
            if (matches) {
                changed = offset + 5;
                break;
            }
        }
        if (changed < 0) throw new AssertionError("No citizen ID in observed frame");
        forged[changed] = (byte) (forged[changed] == 'a' ? 'b' : 'a');
        rewriteCrc(forged, 28);
        Path bad = folder.resolve("corrupt.bin");
        Files.write(bad, forged);
        try (var unexpected = new CausalEvidenceJournal(bad, world)) {
            throw new AssertionError("Rechecksummed forged record was accepted");
        } catch (IOException expected) {
            yes(expected.getMessage().contains("broken hash chain"));
        }

        // A valid header copied from another world must not be accepted.
        rejects(() -> new CausalEvidenceJournal(valid, UUID.randomUUID()));

        // Invalidating one event must never mutate another observed event,
        // even when both were initially admitted in the same file.
        try (var journal = new CausalEvidenceJournal(valid, world)) {
            yes(journal.inspect(b.eventId()).state() == CausalEvidenceJournal.State.REVOKED);
            yes(journal.inspect(a.eventId()).state() == CausalEvidenceJournal.State.ADMITTED);
            yes(!journal.inspect(a.eventId()).activeForAudit());
            yes(journal.reconcile(a.eventId(), receipt -> true).activeForAudit());
            yes(!journal.reconcile(b.eventId(), receipt -> true).activeForAudit());
        }

        System.out.println("CausalEvidenceJournalFaultTest: " + checks
            + " checks passed (all byte-boundary crash cuts + live rollback mismatch)");
    }
}
