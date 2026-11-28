package dev.hearthbound.experiment;

import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.nio.file.attribute.BasicFileAttributes;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Experiment-only durable intent delivery; never mutates a world or chooses a citizen action.
 * A receipt is an adapter assertion, not a verified Minecraft outcome. See the C14 v2 contract.
 * Supported persistence environment: a local Linux filesystem with POSIX record locking.
 */
public final class EventScheduler implements AutoCloseable {
    public static final int MAX_EVENTS = 4096, MAX_LINE_BYTES = 1024, MAX_RECORDS = 100000;
    public static final long MAX_FILE_BYTES = 16L * 1024 * 1024;
    private static final String ZERO_HASH = "0".repeat(64);
    private static final Pattern TOKEN = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._-]{0,63}");
    private static final Pattern DECIMAL = Pattern.compile("0|[1-9][0-9]*");
    private static final Set<String> KINDS = Set.of("crop_failure", "mill_failure", "specialist_loss",
        "resource_depletion", "communication_failure", "demand_change");
    // Check before opening: closing a second descriptor can release POSIX locks on the first.
    private static final Set<Object> OPEN_FILE_KEYS = new HashSet<>();

    public record Event(String eventId, String kind, long onset, long duration, double severity) {
        public Event {
            requireToken(eventId);
            if (kind == null || !KINDS.contains(kind) || onset < 0 || duration <= 0 || onset > Long.MAX_VALUE - duration
                    || !Double.isFinite(severity) || severity < 0 || severity > 1)
                throw new IllegalArgumentException("invalid event");
            if (severity == 0) severity = 0; // canonicalize negative zero
        }
    }
    public record Transition(int index, String transitionId, String eventId, String phase,
                             long tick, String kind, double severity) {}
    public record Intent(Transition transition, long observedTick, boolean recoveryRequired) {
        public boolean executable() { return !recoveryRequired && observedTick == transition.tick(); }
    }
    public enum Outcome { APPLIED, FAILED, MISSED, NOT_APPLIED }
    public record Receipt(int index, String transitionId, Outcome outcome, String evidenceId,
                          Long effectTick, String mode) {}

    /** Immutable, canonical schedule shared by native Java and the Python reference. */
    public static final class Schedule {
        private final List<Event> events;
        private final List<Transition> transitions;
        private final Map<String, Integer> indices;
        private final String digest;
        public Schedule(List<Event> input) {
            if (input == null || input.size() > MAX_EVENTS) throw new IllegalArgumentException("invalid event count");
            var sorted = new ArrayList<Event>();
            var ids = new HashSet<String>();
            for (Event event : input) {
                if (event == null || !ids.add(event.eventId())) throw new IllegalArgumentException("duplicate or null event");
                sorted.add(event);
            }
            sorted.sort(Comparator.comparing(Event::eventId));
            events = List.copyOf(sorted);
            StringBuilder canonical = new StringBuilder("hearthbound:event-schedule:v2\n");
            for (Event event : events) canonical.append(event.eventId()).append('\t').append(event.kind())
                .append('\t').append(event.onset()).append('\t').append(event.duration()).append('\t')
                .append(severityBits(event.severity())).append('\n');
            digest = sha256(canonical.toString().getBytes(StandardCharsets.US_ASCII));
            record Edge(Event event, String phase, long tick) {}
            var edges = new ArrayList<Edge>();
            for (Event event : events) {
                edges.add(new Edge(event, "start", event.onset()));
                edges.add(new Edge(event, "end", event.onset() + event.duration()));
            }
            edges.sort(Comparator.comparingLong(Edge::tick).thenComparing(Edge::phase)
                .thenComparing(edge -> edge.event().eventId())); // ASCII "end" before "start"
            var timeline = new ArrayList<Transition>();
            var lookup = new HashMap<String, Integer>();
            for (Edge edge : edges) {
                int index = timeline.size();
                String id = digest + ":" + edge.event().eventId() + ":" + edge.phase();
                timeline.add(new Transition(index, id, edge.event().eventId(), edge.phase(), edge.tick(),
                    edge.event().kind(), edge.event().severity()));
                lookup.put(id, index);
            }
            transitions = List.copyOf(timeline);
            indices = Map.copyOf(lookup);
        }
        public List<Event> events() { return events; }
        public List<Transition> transitions() { return transitions; }
        public String digest() { return digest; }
    }

    @FunctionalInterface
    interface IoHook { void at(String phase, String operation, FileChannel file) throws IOException; }
    private IoHook ioHook = (phase, operation, channel) -> {};
    void setIoHook(IoHook hook) { ioHook = Objects.requireNonNull(hook); }

    /** Lowered limits for exercising actual journal exhaustion without 100000 fsyncs. */
    record Capacity(int records, long bytes) {
        Capacity {
            if (records < 1 || records > MAX_RECORDS || bytes < MAX_LINE_BYTES || bytes > MAX_FILE_BYTES)
                throw new IllegalArgumentException("capacity must stay within production bounds");
        }
    }
    private static final Capacity PRODUCTION_CAPACITY = new Capacity(MAX_RECORDS, MAX_FILE_BYTES);

    private final Schedule schedule;
    private final Capacity capacity;
    private final String worldId, runId;
    private final FileChannel file;
    private final FileLock lock;
    private final Object fileKey;
    private final List<Receipt> receipts = new ArrayList<>();
    private long clock = -1;
    private int nextIndex;
    private Intent pending;
    private int sequence;
    private long durableBytes;
    private String previousHash = ZERO_HASH;
    private boolean poisoned, closed;

    public static EventScheduler create(Path path, List<Event> events, String world, String run) throws IOException {
        return new EventScheduler(path, new Schedule(events), world, run, true, PRODUCTION_CAPACITY);
    }
    public static EventScheduler open(Path path, List<Event> events, String world, String run) throws IOException {
        return new EventScheduler(path, new Schedule(events), world, run, false, PRODUCTION_CAPACITY);
    }
    static EventScheduler createWithCapacity(Path path, List<Event> events, String world, String run, Capacity capacity) throws IOException {
        return new EventScheduler(path, new Schedule(events), world, run, true, capacity);
    }
    static EventScheduler openWithCapacity(Path path, List<Event> events, String world, String run, Capacity capacity) throws IOException {
        return new EventScheduler(path, new Schedule(events), world, run, false, capacity);
    }

    private EventScheduler(Path path, Schedule schedule, String world, String run, boolean create, Capacity capacity) throws IOException {
        this.schedule = schedule;
        this.capacity = Objects.requireNonNull(capacity);
        requireToken(world); requireToken(run);
        worldId = world; runId = run;
        Path absolute = Objects.requireNonNull(path).toAbsolutePath().normalize();
        FileChannel acquiredFile = null;
        FileLock acquiredLock = null;
        Object acquiredKey = null;
        synchronized (OPEN_FILE_KEYS) {
            try {
                if (Files.exists(absolute, LinkOption.NOFOLLOW_LINKS)) {
                    Object existing = key(absolute);
                    if (OPEN_FILE_KEYS.contains(existing)) throw new IOException("journal already open in this process");
                }
                acquiredFile = create
                    ? FileChannel.open(absolute, StandardOpenOption.CREATE_NEW, StandardOpenOption.READ,
                        StandardOpenOption.WRITE, LinkOption.NOFOLLOW_LINKS)
                    : FileChannel.open(absolute, StandardOpenOption.READ, StandardOpenOption.WRITE,
                        LinkOption.NOFOLLOW_LINKS);
                acquiredKey = key(absolute);
                if (OPEN_FILE_KEYS.contains(acquiredKey)) throw new IOException("journal already open in this process");
                try { acquiredLock = acquiredFile.tryLock(); }
                catch (OverlappingFileLockException e) { throw new IOException("journal already has a writer", e); }
                if (acquiredLock == null) throw new IOException("journal already has a writer");
                OPEN_FILE_KEYS.add(acquiredKey);
            } catch (IOException | RuntimeException e) {
                if (acquiredLock != null) try { acquiredLock.release(); } catch (IOException suppressed) { e.addSuppressed(suppressed); }
                if (acquiredFile != null) try { acquiredFile.close(); } catch (IOException suppressed) { e.addSuppressed(suppressed); }
                throw e;
            }
        }
        file = acquiredFile; lock = acquiredLock; fileKey = acquiredKey;
        try {
            if (create) {
                append("BIND", List.of(world, run, schedule.digest()));
                try (FileChannel directory = FileChannel.open(absolute.getParent(), StandardOpenOption.READ)) {
                    directory.force(true);
                }
            } else {
                replay();
                if (pending != null) pending = new Intent(pending.transition(), pending.observedTick(), true);
            }
        } catch (IOException | RuntimeException e) {
            try { close(); } catch (IOException suppressed) { e.addSuppressed(suppressed); }
            throw e;
        }
    }

    private static Object key(Path path) throws IOException {
        var attrs = Files.readAttributes(path, BasicFileAttributes.class, LinkOption.NOFOLLOW_LINKS);
        if (!attrs.isRegularFile() || attrs.fileKey() == null) throw new IOException("regular file with stable identity required");
        return attrs.fileKey();
    }

    public synchronized Intent poll(long tick) throws IOException {
        healthy();
        if (tick < 0 || tick < clock) throw new IllegalArgumentException("backward or invalid clock");
        if (pending != null) throw new IllegalStateException("outstanding intent requires settlement");
        if (nextIndex < schedule.transitions().size() && schedule.transitions().get(nextIndex).tick() <= tick) {
            append("PREPARE", List.of(Integer.toString(nextIndex), Long.toString(tick)));
            return pending;
        }
        if (tick > clock) append("CLOCK", List.of(Long.toString(tick)));
        return null;
    }

    public synchronized boolean acknowledge(String id, Outcome outcome, String evidence, Long effectTick) throws IOException {
        return settle("ACK", id, outcome, evidence, effectTick);
    }
    public synchronized boolean reconcile(String id, Outcome outcome, String evidence, Long effectTick) throws IOException {
        return settle("RECONCILE", id, outcome, evidence, effectTick);
    }
    private boolean settle(String mode, String id, Outcome outcome, String evidence, Long effectTick) throws IOException {
        healthy();
        String prefix = worldId + ":" + runId + ":";
        Integer index = id == null || !id.startsWith(prefix) ? null : schedule.indices.get(id.substring(prefix.length()));
        if (index == null) throw new IllegalArgumentException("foreign or unknown transition");
        requireToken(evidence);
        if (outcome == null || (effectTick != null && effectTick < 0)) throw new IllegalArgumentException("invalid receipt");
        Receipt receipt = new Receipt(index, id, outcome, evidence, effectTick, mode);
        if (index < nextIndex) {
            if (!receipts.get(index).equals(receipt)) throw new IllegalArgumentException("conflicting duplicate receipt");
            return false;
        }
        if (pending == null || index != nextIndex) throw new IllegalStateException("transition is not pending");
        if (pending.recoveryRequired() != mode.equals("RECONCILE"))
            throw new IllegalStateException("recovered intents require reconciliation; live intents require acknowledgement");
        append(mode, List.of(Integer.toString(index), outcome.name(), effectTick == null ? "-" : effectTick.toString(), evidence));
        return true;
    }

    public synchronized long clock() { healthy(); return clock; }
    public synchronized int nextIndex() { healthy(); return nextIndex; }
    public synchronized Intent pending() { healthy(); return pending; }
    public synchronized List<Receipt> receipts() { healthy(); return List.copyOf(receipts); }
    public Schedule schedule() { return schedule; }
    public String worldId() { return worldId; }
    public String runId() { return runId; }
    public String transitionId(int index) { return worldId + ":" + runId + ":" + schedule.transitions().get(index).transitionId(); }
    private Transition boundTransition(int index) {
        Transition t = schedule.transitions().get(index);
        return new Transition(t.index(), transitionId(index), t.eventId(), t.phase(), t.tick(), t.kind(), t.severity());
    }

    private void append(String operation, List<String> arguments) throws IOException {
        healthy();
        apply(operation, arguments, false);
        // An exposed intent must retain room for its ACK or post-restart RECONCILE.
        int requiredRecords = operation.equals("PREPARE") ? 2 : 1;
        if (sequence > capacity.records() - requiredRecords) throw new IOException("journal record capacity exhausted");
        String payload = sequence + "\t" + previousHash + "\t" + operation + "\t" + String.join("\t", arguments);
        String checksum = sha256(payload.getBytes(StandardCharsets.US_ASCII));
        byte[] bytes = (payload + "\t" + checksum + "\n").getBytes(StandardCharsets.US_ASCII);
        long settlementReserve = operation.equals("PREPARE") ? MAX_LINE_BYTES : 0;
        if (bytes.length > MAX_LINE_BYTES || durableBytes > capacity.bytes() - bytes.length - settlementReserve)
            throw new IOException("journal byte capacity exhausted");
        try {
            if (file.size() != durableBytes) throw new IOException("journal size changed outside scheduler");
            ioHook.at("before_write", operation, file);
            file.position(durableBytes);
            ByteBuffer buffer = ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) if (file.write(buffer) <= 0) throw new IOException("journal write made no progress");
            ioHook.at("after_write", operation, file);
            file.force(true);
            ioHook.at("after_force", operation, file);
        } catch (IOException | RuntimeException e) {
            poisoned = true;
            throw e;
        }
        apply(operation, arguments, true);
        durableBytes += bytes.length;
        previousHash = checksum;
        sequence++;
    }

    /** Validates before appending and again while replaying. No validation failure changes state. */
    private void apply(String operation, List<String> arguments, boolean commit) {
        switch (operation) {
            case "BIND" -> {
                if (sequence != 0 || arguments.size() != 3 || !arguments.get(0).equals(worldId)
                        || !arguments.get(1).equals(runId) || !arguments.get(2).equals(schedule.digest()))
                    throw new IllegalArgumentException("journal binding mismatch");
            }
            case "CLOCK" -> {
                if (sequence == 0 || arguments.size() != 1) throw new IllegalArgumentException("invalid CLOCK");
                long tick = decimal(arguments.get(0));
                if (pending != null || tick <= clock || (nextIndex < schedule.transitions().size()
                        && schedule.transitions().get(nextIndex).tick() <= tick))
                    throw new IllegalArgumentException("CLOCK bypasses a due or pending transition");
                if (commit) clock = tick;
            }
            case "PREPARE" -> {
                if (sequence == 0 || arguments.size() != 2) throw new IllegalArgumentException("invalid PREPARE");
                long index = decimal(arguments.get(0)), tick = decimal(arguments.get(1));
                if (pending != null || index != nextIndex || index >= schedule.transitions().size()
                        || tick < clock || schedule.transitions().get(nextIndex).tick() > tick)
                    throw new IllegalArgumentException("impossible PREPARE");
                if (commit) {
                    clock = tick;
                    pending = new Intent(boundTransition(nextIndex), tick, false);
                }
            }
            case "ACK", "RECONCILE" -> {
                if (sequence == 0 || arguments.size() != 4) throw new IllegalArgumentException("invalid receipt record");
                long index = decimal(arguments.get(0));
                Outcome outcome;
                try { outcome = Outcome.valueOf(arguments.get(1)); }
                catch (RuntimeException e) { throw new IllegalArgumentException("invalid receipt outcome", e); }
                Long effect = arguments.get(2).equals("-") ? null : decimal(arguments.get(2));
                String evidence = arguments.get(3);
                requireToken(evidence);
                if (pending == null || index != nextIndex) throw new IllegalArgumentException("receipt without matching intent");
                boolean onTime = pending.observedTick() == pending.transition().tick();
                boolean valid = switch (outcome) {
                    case APPLIED -> onTime && effect != null && effect == pending.transition().tick();
                    case FAILED -> onTime && effect == null;
                    case MISSED -> !onTime && effect == null;
                    case NOT_APPLIED -> operation.equals("RECONCILE") && effect == null;
                };
                if (!valid) throw new IllegalArgumentException("receipt contradicts intent chronology");
                if (commit) {
                    receipts.add(new Receipt(nextIndex, pending.transition().transitionId(), outcome, evidence, effect, operation));
                    nextIndex++;
                    pending = null;
                }
            }
            default -> throw new IllegalArgumentException("unknown journal operation");
        }
    }

    private void replay() throws IOException {
        long size = file.size();
        if (size == 0 || size > capacity.bytes()) throw new IOException("empty or oversized journal");
        ByteBuffer data = ByteBuffer.allocate((int) size);
        file.position(0);
        while (data.hasRemaining()) if (file.read(data) <= 0) throw new IOException("journal read truncated or made no progress");
        byte[] bytes = data.array();
        int start = 0;
        for (int i = 0; i < bytes.length; i++) {
            int value = Byte.toUnsignedInt(bytes[i]);
            if ((value < 32 && value != '\t' && value != '\n') || value > 126)
                throw new IOException("noncanonical journal byte");
            if (i - start + 1 > MAX_LINE_BYTES) throw new IOException("oversized journal record");
            if (value != '\n') continue;
            if (sequence >= capacity.records()) throw new IOException("journal record capacity exceeded");
            String line = new String(bytes, start, i - start, StandardCharsets.US_ASCII);
            String[] fields = line.split("\t", -1);
            if (fields.length < 5) throw new IOException("short journal record");
            int lastTab = line.lastIndexOf('\t');
            String checksum = sha256(line.substring(0, lastTab).getBytes(StandardCharsets.US_ASCII));
            try {
                if (decimal(fields[0]) != sequence || !fields[1].equals(previousHash)
                        || !fields[fields.length - 1].equals(checksum))
                    throw new IllegalArgumentException("journal sequence or checksum mismatch");
                var arguments = new ArrayList<String>();
                for (int f = 3; f < fields.length - 1; f++) arguments.add(fields[f]);
                apply(fields[2], arguments, true);
            } catch (IllegalArgumentException | IllegalStateException e) {
                throw new IOException("invalid journal record " + sequence + ": " + e.getMessage(), e);
            }
            previousHash = checksum;
            sequence++;
            start = i + 1;
        }
        if (start != bytes.length || sequence == 0) throw new IOException("torn journal record");
        if (file.size() != size) throw new IOException("journal size changed during replay");
        durableBytes = size;
        file.position(size);
    }

    private static long decimal(String text) {
        if (!DECIMAL.matcher(text).matches()) throw new IllegalArgumentException("noncanonical decimal");
        try { return Long.parseLong(text); }
        catch (NumberFormatException e) { throw new IllegalArgumentException("decimal overflow", e); }
    }
    private static void requireToken(String value) {
        if (value == null || !TOKEN.matcher(value).matches()) throw new IllegalArgumentException("invalid identity token");
    }
    public static String severityBits(double severity) {
        return HexFormat.of().toHexDigits(Double.doubleToRawLongBits(severity == 0 ? 0 : severity));
    }
    private static String sha256(byte[] value) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(value)); }
        catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
    private void healthy() {
        if (closed || poisoned) throw new IllegalStateException("journal closed or poisoned by uncertain I/O");
    }
    @Override public synchronized void close() throws IOException {
        if (closed) return;
        closed = true;
        IOException failure = null;
        try { lock.release(); } catch (IOException e) { failure = e; }
        try { file.close(); } catch (IOException e) { if (failure == null) failure = e; else failure.addSuppressed(e); }
        finally { synchronized (OPEN_FILE_KEYS) { OPEN_FILE_KEYS.remove(fileKey); } }
        if (failure != null) throw failure;
    }
}
