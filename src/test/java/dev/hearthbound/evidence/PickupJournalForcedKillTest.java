package dev.hearthbound.evidence;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

/**
 * Real OS process termination of the storage-only journal, NOT a Minecraft
 * inventory test. Every child is killed forcibly without AutoCloseable.close().
 *
 * Parent uses the same Java 17 test classpath; child prints READY only after
 * force(true) returns. The parent never treats the READY message as a physical
 * pickup or proof of a committed Minecraft block-entity change.
 */
public final class PickupJournalForcedKillTest {
    private static final String READY = "PICKUP_JOURNAL_FORCE_COMPLETE";
    private static void check(boolean ok, String reason) {
        if (!ok) throw new AssertionError(reason);
    }
    private static PickupTransactionJournal.Intent intent(UUID world, UUID job, UUID actor) {
        return new PickupTransactionJournal.Intent(
            world, job, actor, "minecraft:overworld|3,80,3", "reported-wheat", 5, 8);
    }
    private static void child(String[] args) throws Exception {
        Path file = Path.of(args[1]);
        UUID world = UUID.fromString(args[2]);
        UUID job = UUID.fromString(args[3]);
        UUID actor = UUID.fromString(args[4]);
        String boundary = args[5];
        try (PickupTransactionJournal journal = new PickupTransactionJournal(file, world)) {
            if (!"BEFORE_INTENT".equals(boundary)) {
                journal.begin(intent(world, job, actor));
                if ("AFTER_EMPTY_OUTCOME".equals(boundary))
                    journal.finish(job, PickupTransactionJournal.State.EXTRACTION_EMPTY);
                if ("AFTER_CARGO_OUTCOME".equals(boundary))
                    journal.finish(job, PickupTransactionJournal.State.CARGO_RETURNED);
            }
            System.out.println(READY + " " + boundary);
            System.out.flush();
            // Parent must terminate the JVM before close(), not send a polite
            // interrupt/shutdown hook. A test timeout is a hard failure.
            Thread.sleep(120_000L);
        }
    }
    private static PickupTransactionJournal.View run(Path root, String boundary)
            throws Exception {
        UUID world = UUID.randomUUID(), job = UUID.randomUUID(), actor = UUID.randomUUID();
        Path journalPath = root.resolve(boundary + ".bin");
        String javaBinary = Path.of(System.getProperty("java.home"),
            "bin", "java").toString();
        Process child = new ProcessBuilder(javaBinary, "-cp",
            System.getProperty("java.class.path"),
            PickupJournalForcedKillTest.class.getName(), "child",
            journalPath.toString(), world.toString(), job.toString(),
            actor.toString(), boundary).redirectErrorStream(true).start();
        try {
            // Do not use readLine without a deadline: a broken child could hang.
            var line = java.util.concurrent.CompletableFuture.supplyAsync(() -> {
                try (BufferedReader reader = new BufferedReader(
                        new InputStreamReader(child.getInputStream()))) {
                    return reader.readLine();
                } catch (IOException failure) {
                    throw new java.util.concurrent.CompletionException(failure);
                }
            }).get(15, TimeUnit.SECONDS);
            check((READY + " " + boundary).equals(line),
                "child never reported a successful durable boundary: " + line);
            check(child.isAlive(), "child died before forced termination");
            child.destroyForcibly();
            check(child.waitFor(10, TimeUnit.SECONDS), "child did not terminate");
            check(!child.isAlive(), "child still alive");
        } finally {
            if (child.isAlive()) {
                child.destroyForcibly();
                child.waitFor(10, TimeUnit.SECONDS);
            }
        }
        try (PickupTransactionJournal reopened =
                 new PickupTransactionJournal(journalPath, world)) {
            return reopened.inspect(job);
        }
    }
    public static void main(String[] args) throws Exception {
        if (args.length > 0 && "child".equals(args[0])) {
            child(args);
            return;
        }
        Path root = Files.createTempDirectory("hearthbound-killed-journal-");
        check(run(root, "BEFORE_INTENT") == null,
            "pre-intent crash must not fabricate an intent");
        PickupTransactionJournal.View pending = run(root, "AFTER_INTENT");
        check(pending != null && pending.state() == PickupTransactionJournal.State.UNRESOLVED,
            "post-intent crash must leave an unresolved/quarantined record");
        PickupTransactionJournal.View empty = run(root, "AFTER_EMPTY_OUTCOME");
        check(empty != null && empty.state() == PickupTransactionJournal.State.EXTRACTION_EMPTY,
            "post-empty-outcome crash must retain empty extraction evidence");
        PickupTransactionJournal.View cargo = run(root, "AFTER_CARGO_OUTCOME");
        check(cargo != null && cargo.state() == PickupTransactionJournal.State.CARGO_RETURNED,
            "post-cargo-outcome crash must retain cargo result without proving delivery");
        System.out.println("PickupJournalForcedKillTest passed (storage layer only)");
    }
}
