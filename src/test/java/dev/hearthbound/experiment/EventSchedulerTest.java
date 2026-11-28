package dev.hearthbound.experiment;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;

/** Standalone contract/fault tests. No Minecraft effects or agent adaptation are asserted. */
public final class EventSchedulerTest {
    @FunctionalInterface interface Checked { void run() throws Exception; }
    static int passed;
    static final List<EventScheduler.Event> EVENTS = List.of(new EventScheduler.Event("a", "crop_failure", 2, 3, .5));
    static void check(boolean condition) { if (!condition) throw new AssertionError("contract failed"); }
    static void reject(Checked body) throws Exception {
        try { body.run(); } catch (IOException | IllegalArgumentException | IllegalStateException expected) { return; }
        throw new AssertionError("invalid operation accepted");
    }
    static void test(String name, Checked body) throws Exception { body.run(); passed++; System.out.println("PASS " + name); }
    static Path fresh() throws IOException { return Files.createTempDirectory("hearthbound-event-java-").resolve("events.log"); }
    static EventScheduler create(Path path) throws IOException { return EventScheduler.create(path, EVENTS, "world", "run"); }
    static EventScheduler open(Path path) throws IOException { return EventScheduler.open(path, EVENTS, "world", "run"); }
    static String hash(String value) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.US_ASCII)));
    }
    static void forge(Path path, List<String> records) throws Exception {
        String previous = "0".repeat(64);
        StringBuilder content = new StringBuilder();
        for (int index = 0; index < records.size(); index++) {
            String payload = index + "\t" + previous + "\t" + records.get(index);
            previous = hash(payload);
            content.append(payload).append('\t').append(previous).append('\n');
        }
        Files.writeString(path, content, StandardCharsets.US_ASCII);
    }
    static String binding() { return "BIND\tworld\trun\t" + new EventScheduler.Schedule(EVENTS).digest(); }
    public static void main(String[] args) throws Exception {
        test("input validation and bounded times", () -> {
            reject(() -> new EventScheduler.Event("bad id", "crop_failure", 2, 3, .5));
            reject(() -> new EventScheduler.Event("é", "crop_failure", 2, 3, .5));
            reject(() -> new EventScheduler.Event("a", null, 2, 3, .5));
            reject(() -> new EventScheduler.Event("a", "unknown", 2, 3, .5));
            reject(() -> new EventScheduler.Event("a", "crop_failure", -1, 3, .5));
            reject(() -> new EventScheduler.Event("a", "crop_failure", 2, 0, .5));
            reject(() -> new EventScheduler.Event("a", "crop_failure", Long.MAX_VALUE, 1, .5));
            for (double bad : new double[] {Double.NaN, Double.POSITIVE_INFINITY, -.01, 1.01})
                reject(() -> new EventScheduler.Event("a", "crop_failure", 2, 3, bad));
            check(new EventScheduler.Event("edge", "mill_failure", Long.MAX_VALUE - 1, 1, 1).duration() == 1);
            reject(() -> new EventScheduler.Schedule(List.of(EVENTS.get(0), EVENTS.get(0))));
            var huge = new ArrayList<EventScheduler.Event>();
            for (int i = 0; i <= EventScheduler.MAX_EVENTS; i++) huge.add(new EventScheduler.Event("e" + i, "crop_failure", 0, 1, 1));
            reject(() -> new EventScheduler.Schedule(huge));
        });
        test("canonical ordering and negative zero", () -> {
            var a = new EventScheduler.Event("a", "crop_failure", 2, 3, -0.0);
            var b = new EventScheduler.Event("b", "mill_failure", 5, 3, .1);
            var c = new EventScheduler.Event("c", "specialist_loss", 3, 3, 1);
            var schedule = new EventScheduler.Schedule(List.of(c, b, a));
            check(schedule.digest().equals(new EventScheduler.Schedule(List.of(a, b, c)).digest()));
            check(new EventScheduler.Schedule(List.of(a)).digest().equals(new EventScheduler.Schedule(List.of(
                new EventScheduler.Event("a", "crop_failure", 2, 3, 0.0))).digest()));
            check(EventScheduler.severityBits(-0.0).equals("0000000000000000"));
            check(EventScheduler.severityBits(Double.MIN_VALUE).equals("0000000000000001"));
            check(schedule.transitions().stream().map(t -> t.tick() + ":" + t.phase() + ":" + t.eventId()).toList()
                .equals(List.of("2:start:a", "3:start:c", "5:end:a", "5:start:b", "6:end:c", "8:end:b")));
            try { schedule.events().clear(); throw new AssertionError(); } catch (UnsupportedOperationException expected) {}
        });
        test("empty no-shock control and repeated clock", () -> {
            Path path = fresh();
            try (var scheduler = EventScheduler.create(path, List.of(), "world", "control")) {
                check(scheduler.poll(0) == null); long size = Files.size(path);
                check(scheduler.poll(0) == null && Files.size(path) == size);
                check(scheduler.poll(10) == null && scheduler.clock() == 10);
                reject(() -> scheduler.poll(9)); check(scheduler.receipts().isEmpty());
            }
            try (var scheduler = EventScheduler.open(path, List.of(), "world", "control")) { check(scheduler.clock() == 10); }
        });
        test("on-time boundary receipts and idempotence", () -> {
            Path path = fresh();
            try (var scheduler = create(path)) {
                check(scheduler.poll(1) == null);
                var intent = scheduler.poll(2); check(intent.executable() && !intent.recoveryRequired());
                reject(() -> scheduler.poll(2));
                String id = intent.transition().transitionId();
                reject(() -> scheduler.acknowledge(id, EventScheduler.Outcome.APPLIED, "proof", 3L));
                reject(() -> scheduler.acknowledge(id, EventScheduler.Outcome.MISSED, "proof", null));
                reject(() -> scheduler.acknowledge(id, EventScheduler.Outcome.NOT_APPLIED, "proof", null));
                reject(() -> scheduler.reconcile(id, EventScheduler.Outcome.APPLIED, "proof", 2L));
                check(scheduler.acknowledge(id, EventScheduler.Outcome.APPLIED, "proof", 2L));
                long size = Files.size(path);
                check(!scheduler.acknowledge(id, EventScheduler.Outcome.APPLIED, "proof", 2L));
                check(Files.size(path) == size);
                reject(() -> scheduler.acknowledge(id, EventScheduler.Outcome.APPLIED, "other", 2L));
                reject(() -> scheduler.reconcile(id, EventScheduler.Outcome.APPLIED, "proof", 2L));
                check(scheduler.poll(4) == null);
                var end = scheduler.poll(5); check(end.transition().phase().equals("end"));
                check(scheduler.acknowledge(end.transition().transitionId(), EventScheduler.Outcome.FAILED, "adapter-failed", null));
                check(scheduler.poll(5) == null && scheduler.nextIndex() == 2);
                try { scheduler.receipts().clear(); throw new AssertionError(); } catch (UnsupportedOperationException expected) {}
            }
            try (var scheduler = open(path)) { check(scheduler.nextIndex() == 2 && scheduler.pending() == null && scheduler.receipts().size() == 2); }
        });
        test("skipped ticks produce only MISSED receipts", () -> {
            Path path = fresh();
            try (var scheduler = create(path)) {
                for (int index = 0; index < 2; index++) {
                    var pending = scheduler.poll(10); check(!pending.executable());
                    String id = pending.transition().transitionId();
                    reject(() -> scheduler.acknowledge(id, EventScheduler.Outcome.APPLIED, "false-proof", pending.transition().tick()));
                    reject(() -> scheduler.acknowledge(id, EventScheduler.Outcome.FAILED, "false-proof", null));
                    check(scheduler.acknowledge(id, EventScheduler.Outcome.MISSED, "missed-" + index, null));
                }
                check(scheduler.poll(10) == null && scheduler.receipts().size() == 2);
            }
        });
        test("restart retains uncertainty and requires explicit reconciliation", () -> {
            Path path = fresh(); String id;
            try (var scheduler = create(path)) { id = scheduler.poll(2).transition().transitionId(); }
            try (var scheduler = open(path)) {
                check(scheduler.pending().recoveryRequired() && !scheduler.pending().executable());
                reject(() -> scheduler.poll(2));
                reject(() -> scheduler.acknowledge(id, EventScheduler.Outcome.APPLIED, "proof", 2L));
                check(scheduler.reconcile(id, EventScheduler.Outcome.NOT_APPLIED, "independent-no-effect", null));
                check(!scheduler.reconcile(id, EventScheduler.Outcome.NOT_APPLIED, "independent-no-effect", null));
                check(scheduler.poll(3) == null);
            }
            try (var scheduler = open(path)) {
                check(scheduler.receipts().get(0).mode().equals("RECONCILE"));
                check(scheduler.receipts().get(0).outcome() == EventScheduler.Outcome.NOT_APPLIED);
                var end = scheduler.poll(6); check(!end.executable());
                scheduler.acknowledge(end.transition().transitionId(), EventScheduler.Outcome.MISSED, "late-end", null);
            }
        });
        test("independent post-restart applied witness", () -> {
            Path path = fresh(); String id;
            try (var scheduler = create(path)) { id = scheduler.poll(2).transition().transitionId(); }
            try (var scheduler = open(path)) {
                scheduler.reconcile(id, EventScheduler.Outcome.APPLIED, "current-world-witness", 2L);
                check(scheduler.receipts().get(0).effectTick() == 2);
            }
        });
        test("world, run, schedule and receipt identity binding", () -> {
            Path path = fresh(); String id;
            try (var scheduler = create(path)) {
                id = scheduler.poll(2).transition().transitionId();
                String foreignWorld = id.replaceFirst("world:", "other:");
                String foreignRun = id.replace(":run:", ":other:");
                reject(() -> scheduler.acknowledge(foreignWorld, EventScheduler.Outcome.APPLIED, "proof", 2L));
                reject(() -> scheduler.acknowledge(foreignRun, EventScheduler.Outcome.APPLIED, "proof", 2L));
                reject(() -> scheduler.acknowledge(scheduler.schedule().transitions().get(0).transitionId(), EventScheduler.Outcome.APPLIED, "proof", 2L));
                reject(() -> scheduler.acknowledge(null, EventScheduler.Outcome.APPLIED, "proof", 2L));
            }
            reject(() -> EventScheduler.open(path, EVENTS, "other", "run"));
            reject(() -> EventScheduler.open(path, EVENTS, "world", "other"));
            reject(() -> EventScheduler.open(path, List.of(), "world", "run"));
            try (var scheduler = open(path)) { check(scheduler.pending().transition().transitionId().equals(id)); }
        });
        test("same-process writer exclusion including hard links", () -> {
            Path path = fresh(); Path alias = path.resolveSibling("alias.log");
            try (var scheduler = create(path)) {
                Files.createLink(alias, path);
                reject(() -> open(path)); reject(() -> open(alias)); reject(() -> create(path));
                check(scheduler.poll(1) == null);
            }
            try (var scheduler = open(alias)) { check(scheduler.clock() == 1); }
        });
        test("exclusive creation and empty file rejection", () -> {
            Path path = fresh(); Files.createFile(path);
            reject(() -> create(path)); reject(() -> open(path)); check(Files.size(path) == 0);
            Path absent = path.resolveSibling("absent"); reject(() -> open(absent)); check(!Files.exists(absent));
            Path symlink = path.resolveSibling("symlink"); Files.createSymbolicLink(symlink, path);
            reject(() -> open(symlink));
        });
        for (String phase : List.of("before_write", "after_write", "after_force")) {
            test("PREPARE I/O fault at " + phase, () -> {
                Path path = fresh();
                try (var scheduler = create(path)) {
                    scheduler.setIoHook((at, op, file) -> { if (at.equals(phase) && op.equals("PREPARE")) throw new IOException("injected fault"); });
                    reject(() -> scheduler.poll(2)); reject(() -> scheduler.poll(2)); reject(scheduler::clock);
                }
                try (var scheduler = open(path)) {
                    if (phase.equals("before_write")) { check(scheduler.pending() == null && scheduler.clock() == -1); }
                    else { check(scheduler.pending().recoveryRequired() && !scheduler.pending().executable()); }
                }
            });
        }
        test("receipt durable before lost response", () -> {
            Path path = fresh(); String id;
            try (var scheduler = create(path)) {
                id = scheduler.poll(2).transition().transitionId();
                scheduler.setIoHook((phase, op, file) -> { if (phase.equals("after_force") && op.equals("ACK")) throw new IOException("lost response"); });
                reject(() -> scheduler.acknowledge(id, EventScheduler.Outcome.APPLIED, "verified", 2L));
                reject(() -> scheduler.poll(3));
            }
            try (var scheduler = open(path)) {
                check(scheduler.pending() == null && scheduler.nextIndex() == 1);
                check(!scheduler.acknowledge(id, EventScheduler.Outcome.APPLIED, "verified", 2L));
            }
        });
        test("torn, corrupt and oversized journals fail closed without repair", () -> {
            Path source = fresh();
            try (var scheduler = create(source)) { scheduler.poll(2); }
            byte[] original = Files.readAllBytes(source);
            for (int length : new int[] {0, 1, original.length / 3, original.length - 1}) {
                Path path = fresh(); byte[] cut = java.util.Arrays.copyOf(original, length); Files.write(path, cut);
                reject(() -> open(path)); check(java.util.Arrays.equals(cut, Files.readAllBytes(path)));
            }
            Path corrupt = fresh(); byte[] damaged = original.clone(); damaged[20] ^= 1; Files.write(corrupt, damaged);
            reject(() -> open(corrupt)); check(java.util.Arrays.equals(damaged, Files.readAllBytes(corrupt)));
            Path huge = fresh(); Files.write(huge, new byte[(int) EventScheduler.MAX_FILE_BYTES + 1]); reject(() -> open(huge));
        });
        test("valid checksum cannot admit impossible lifecycle", () -> {
            for (List<String> records : List.of(
                    List.of(binding(), "CLOCK\t2"),
                    List.of(binding(), "CLOCK\t01"),
                    List.of(binding(), "CLOCK\t1", "CLOCK\t1"),
                    List.of(binding(), "PREPARE\t0\t1"),
                    List.of(binding(), "PREPARE\t1\t5"),
                    List.of(binding(), "ACK\t0\tAPPLIED\t2\tproof"),
                    List.of(binding(), "PREPARE\t0\t2", "CLOCK\t3"),
                    List.of(binding(), "PREPARE\t0\t2", "ACK\t0\tMISSED\t-\tproof"),
                    List.of(binding(), "PREPARE\t0\t2", "ACK\t0\tAPPLIED\t3\tproof"),
                    List.of(binding(), "PREPARE\t0\t2", "ACK\t0\tNOT_APPLIED\t-\tproof"),
                    List.of(binding(), "PREPARE\t0\t3", "ACK\t0\tFAILED\t-\tproof"),
                    List.of(binding(), "PREPARE\t0\t2", "ACK\t0\tAPPLIED\t2\tproof", "ACK\t0\tAPPLIED\t2\tproof"),
                    List.of(binding(), "UNKNOWN\t0"))) {
                Path path = fresh(); forge(path, records); byte[] before = Files.readAllBytes(path);
                reject(() -> open(path)); check(java.util.Arrays.equals(before, Files.readAllBytes(path)));
            }
        });
        test("external file length changes poison rather than append", () -> {
            for (boolean truncate : List.of(false, true)) {
                Path path = fresh();
                try (var scheduler = create(path)) {
                    if (truncate) Files.write(path, new byte[0], StandardOpenOption.TRUNCATE_EXISTING);
                    else Files.writeString(path, "unexpected", StandardOpenOption.APPEND);
                    byte[] before = Files.readAllBytes(path);
                    reject(() -> scheduler.poll(2)); reject(() -> scheduler.poll(2));
                    check(java.util.Arrays.equals(before, Files.readAllBytes(path)));
                }
            }
        });
        test("PREPARE reserves the last settlement record", () -> {
            Path blocked = fresh();
            var oneLeft = new EventScheduler.Capacity(2, EventScheduler.MAX_FILE_BYTES);
            try (var scheduler = EventScheduler.createWithCapacity(blocked, EVENTS, "world", "run", oneLeft)) {
                byte[] before = Files.readAllBytes(blocked);
                reject(() -> scheduler.poll(2));
                check(scheduler.pending() == null && scheduler.clock() == -1 && scheduler.nextIndex() == 0);
                check(java.util.Arrays.equals(before, Files.readAllBytes(blocked)));
            }
            try (var scheduler = EventScheduler.openWithCapacity(blocked, EVENTS, "world", "run", oneLeft)) {
                check(scheduler.pending() == null && scheduler.nextIndex() == 0);
            }
            Path exact = fresh();
            var twoLeft = new EventScheduler.Capacity(3, EventScheduler.MAX_FILE_BYTES);
            try (var scheduler = EventScheduler.createWithCapacity(exact, EVENTS, "world", "run", twoLeft)) {
                var intent = scheduler.poll(2);
                check(scheduler.acknowledge(intent.transition().transitionId(), EventScheduler.Outcome.APPLIED, "witness", 2L));
                byte[] before = Files.readAllBytes(exact);
                reject(() -> scheduler.poll(5));
                check(scheduler.pending() == null && scheduler.nextIndex() == 1);
                check(java.util.Arrays.equals(before, Files.readAllBytes(exact)));
            }
            try (var scheduler = EventScheduler.openWithCapacity(exact, EVENTS, "world", "run", twoLeft)) {
                check(scheduler.pending() == null && scheduler.receipts().size() == 1);
            }
        });
        test("PREPARE reserves bytes for reconciliation after reopen", () -> {
            Path measured = fresh();
            long preparedBytes;
            try (var scheduler = create(measured)) { scheduler.poll(2); preparedBytes = Files.size(measured); }
            long exactBytes = preparedBytes + EventScheduler.MAX_LINE_BYTES;
            Path blocked = fresh();
            var shortByOne = new EventScheduler.Capacity(10, exactBytes - 1);
            try (var scheduler = EventScheduler.createWithCapacity(blocked, EVENTS, "world", "run", shortByOne)) {
                byte[] before = Files.readAllBytes(blocked);
                reject(() -> scheduler.poll(2));
                check(scheduler.pending() == null && scheduler.clock() == -1);
                check(java.util.Arrays.equals(before, Files.readAllBytes(blocked)));
            }
            Path exact = fresh(); String id;
            var enough = new EventScheduler.Capacity(3, exactBytes);
            try (var scheduler = EventScheduler.createWithCapacity(exact, EVENTS, "world", "run", enough)) {
                id = scheduler.poll(2).transition().transitionId();
            }
            try (var scheduler = EventScheduler.openWithCapacity(exact, EVENTS, "world", "run", enough)) {
                check(scheduler.pending().recoveryRequired());
                check(scheduler.reconcile(id, EventScheduler.Outcome.APPLIED, "e".repeat(64), 2L));
                check(scheduler.pending() == null && scheduler.nextIndex() == 1 && Files.size(exact) <= exactBytes);
            }
            try (var scheduler = EventScheduler.openWithCapacity(exact, EVENTS, "world", "run", enough)) {
                check(scheduler.receipts().get(0).mode().equals("RECONCILE"));
            }
            reject(() -> new EventScheduler.Capacity(EventScheduler.MAX_RECORDS + 1, EventScheduler.MAX_FILE_BYTES));
            reject(() -> new EventScheduler.Capacity(10, EventScheduler.MAX_FILE_BYTES + 1));
        });
        test("closed scheduler cannot continue", () -> {
            var scheduler = create(fresh()); scheduler.close(); scheduler.close();
            reject(() -> scheduler.poll(1)); reject(scheduler::receipts);
        });
        System.out.println("PASS " + passed + " Java event scheduler contract groups; Forge and physical effects not executed");
    }
}
