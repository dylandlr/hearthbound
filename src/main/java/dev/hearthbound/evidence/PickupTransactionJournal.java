package dev.hearthbound.evidence;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.*;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.zip.CRC32;

/**
 * Crash-durable, world-bound extraction audit. Does NOT move items, heal NBT,
 * authorize rewards, or prove an inventory is empty. A missing outcome is
 * UNKNOWN: never retry or resume a restored job automatically.
 *
 * The caller MUST force begin() before invoking the real extract operation and
 * force finish() after the call. On I/O failure the caller must fail closed.
 */
public final class PickupTransactionJournal implements AutoCloseable {
    private static final int MAGIC = 0x4842504a; // HBPJ
    private static final int VERSION = 1;
    private static final int MAX_PAYLOAD = 16384;
    private final UUID world;
    private final FileChannel channel;
    private final FileLock lock;
    private final Map<UUID, Entry> entries = new LinkedHashMap<>();
    private byte[] previous = new byte[32];
    private long sequence = 1;
    private boolean poisoned, closed;

    public enum State { UNRESOLVED, EXTRACTION_EMPTY, CARGO_RETURNED }
    public enum DeliveryState { NOT_STARTED, INSERTION_UNRESOLVED, INSERTION_RETURNED }
    public record Intent(UUID world, UUID job, UUID executor, String source,
                         String reportId, long assignedTick, long attemptedTick) {
        public Intent {
            Objects.requireNonNull(world);
            Objects.requireNonNull(job);
            Objects.requireNonNull(executor);
            if (source == null || source.isBlank() || source.length() > 512
                    || reportId == null || reportId.isBlank() || reportId.length() > 512
                    || assignedTick < 0 || attemptedTick < assignedTick)
                throw new IllegalArgumentException("invalid extraction intent");
        }
    }
    public record View(Intent intent, State state) {
        public boolean requiresQuarantine() { return state == State.UNRESOLVED; }
    }
    private static final class Entry {
        final Intent intent;
        State state = State.UNRESOLVED;
        DeliveryState delivery = DeliveryState.NOT_STARTED;
        String destination = "";
        long deliveryTick = -1;
        Entry(Intent intent) { this.intent = intent; }
        View view() { return new View(intent, state); }
    }

    public PickupTransactionJournal(Path path, UUID world) throws IOException {
        this.world = Objects.requireNonNull(world);
        Path absolute = Objects.requireNonNull(path).toAbsolutePath().normalize();
        if (Files.isSymbolicLink(absolute) || Files.isSymbolicLink(absolute.getParent()))
            throw new IOException("symlink journal path");
        Files.createDirectories(absolute.getParent());
        channel = FileChannel.open(absolute, StandardOpenOption.CREATE, StandardOpenOption.READ,
            StandardOpenOption.WRITE);
        FileLock acquired = null;
        try {
            try { acquired = channel.tryLock(); }
            catch (OverlappingFileLockException e) { throw new IOException("writer already active", e); }
            if (acquired == null) throw new IOException("writer already active");
            lock = acquired;
            load();
        } catch (IOException | RuntimeException e) {
            if (acquired != null) try { acquired.release(); } catch (IOException x) { e.addSuppressed(x); }
            try { channel.close(); } catch (IOException x) { e.addSuppressed(x); }
            throw e;
        }
    }

    /** Must return before extraction begins; requires a real, validated job. */
    public synchronized void begin(Intent intent) throws IOException {
        healthy();
        Objects.requireNonNull(intent);
        if (!world.equals(intent.world())) throw new IOException("foreign-world extraction");
        if (entries.containsKey(intent.job())) throw new IOException("duplicate pickup job");
        append((byte)1, intent, null);
        entries.put(intent.job(), new Entry(intent));
    }

    /** Only the actual motor may call this, after extractItem returned. */
    public synchronized void finish(UUID job, State outcome) throws IOException {
        healthy();
        if (outcome == null || outcome == State.UNRESOLVED)
            throw new IllegalArgumentException("physical extraction outcome required");
        Entry entry = entries.get(job);
        if (entry == null || entry.state != State.UNRESOLVED)
            throw new IOException("unknown or already resolved pickup job");
        append((byte)(outcome == State.EXTRACTION_EMPTY ? 2 : 3), entry.intent, outcome);
        entry.state = outcome;
    }

    /**
     * Force delivery intent BEFORE the real inventory insertion call.
     * A replayed intent without a returned result is never retried.
     */
    public synchronized void beginDelivery(DeliveryBoundaryContract.Intent delivery)
            throws IOException {
        healthy();
        Objects.requireNonNull(delivery);
        Entry entry = entries.get(delivery.job());
        DeliveryBoundaryContract.Decision permission =
            DeliveryBoundaryContract.admit(entry == null ? null : entry.view(),
                delivery, true, entry != null && entry.delivery != DeliveryState.NOT_STARTED);
        if (permission != DeliveryBoundaryContract.Decision.ADMIT_INSERTION_INTENT)
            throw new IOException("delivery intent denied: " + permission);
        appendDelivery((byte)4, delivery.job(), delivery.destination(), delivery.attemptedTick());
        entry.destination = delivery.destination();
        entry.deliveryTick = delivery.attemptedTick();
        entry.delivery = DeliveryState.INSERTION_UNRESOLVED;
    }

    /** Recorded after the physical insertion motor returns no remainder.
     * This records the call's return, NOT an independently saved delivery. */
    public synchronized void finishDelivery(UUID job) throws IOException {
        healthy();
        Entry entry = entries.get(job);
        if (entry == null || entry.delivery != DeliveryState.INSERTION_UNRESOLVED)
            throw new IOException("missing or completed insertion intent");
        appendDelivery((byte)5, job, "", 0);
        entry.delivery = DeliveryState.INSERTION_RETURNED;
    }

    public synchronized DeliveryState inspectDelivery(UUID job) {
        healthy();
        Entry entry = entries.get(job);
        return entry == null ? null : entry.delivery;
    }

    private void appendDelivery(byte type, UUID job, String destination, long tick)
            throws IOException {
        byte[] payload;
        try (ByteArrayOutputStream bytes = new ByteArrayOutputStream();
             DataOutputStream out = new DataOutputStream(bytes)) {
            out.writeLong(sequence);
            out.write(previous);
            out.writeByte(type);
            out.writeLong(job.getMostSignificantBits());
            out.writeLong(job.getLeastSignificantBits());
            if (type == 4) {
                out.writeUTF(destination);
                out.writeLong(tick);
            }
            out.flush();
            payload = bytes.toByteArray();
        }
        forceFrame(payload);
    }

    public synchronized View inspect(UUID job) {
        healthy();
        Entry entry = entries.get(job);
        return entry == null ? null : entry.view();
    }

    /** Immutable snapshot includes jobs whose villagers are currently unloaded. */
    public synchronized List<View> snapshot() {
        healthy();
        List<View> result = new ArrayList<>();
        for (Entry entry : entries.values()) result.add(entry.view());
        return List.copyOf(result);
    }

    public synchronized List<View> unresolved() {
        healthy();
        List<View> result = new ArrayList<>();
        for (Entry entry : entries.values())
            if (entry.state == State.UNRESOLVED) result.add(entry.view());
        return List.copyOf(result);
    }

    private void append(byte type, Intent intent, State outcome) throws IOException {
        byte[] payload;
        try (ByteArrayOutputStream bytes = new ByteArrayOutputStream();
             DataOutputStream out = new DataOutputStream(bytes)) {
            out.writeLong(sequence);
            out.write(previous);
            out.writeByte(type);
            out.writeLong(intent.job().getMostSignificantBits());
            out.writeLong(intent.job().getLeastSignificantBits());
            if (type == 1) {
                out.writeLong(intent.executor().getMostSignificantBits());
                out.writeLong(intent.executor().getLeastSignificantBits());
                out.writeUTF(intent.source());
                out.writeUTF(intent.reportId());
                out.writeLong(intent.assignedTick());
                out.writeLong(intent.attemptedTick());
            }
            out.flush();
            payload = bytes.toByteArray();
        }
        forceFrame(payload);
    }

    private void forceFrame(byte[] payload) throws IOException {
        if (payload.length > MAX_PAYLOAD) throw new IOException("oversized extraction frame");
        CRC32 crc = new CRC32();
        crc.update(payload);
        ByteBuffer frame = ByteBuffer.allocate(payload.length + 8)
            .putInt(payload.length).putInt((int)crc.getValue()).put(payload);
        frame.flip();
        try {
            channel.position(channel.size());
            writeFully(frame);
            channel.force(true);
        } catch (IOException | RuntimeException e) {
            poisoned = true;
            throw e;
        }
        previous = hash(payload);
        sequence++;
    }

    private void load() throws IOException {
        if (channel.size() == 0) {
            ByteBuffer header = ByteBuffer.allocate(24).putInt(MAGIC).putInt(VERSION)
                .putLong(world.getMostSignificantBits()).putLong(world.getLeastSignificantBits());
            header.flip();
            writeFully(header);
            channel.force(true);
        } else {
            if (channel.size() < 24) throw new IOException("truncated pickup header");
            ByteBuffer header = ByteBuffer.allocate(24);
            readFully(header);
            header.flip();
            if (header.getInt() != MAGIC || header.getInt() != VERSION
                || !world.equals(new UUID(header.getLong(), header.getLong())))
                throw new IOException("pickup journal world/version mismatch");
        }
        while (channel.position() < channel.size()) {
            ByteBuffer header = ByteBuffer.allocate(8);
            readFully(header);
            header.flip();
            int length = header.getInt();
            int checksum = header.getInt();
            if (length < 57 || length > MAX_PAYLOAD) throw new IOException("invalid pickup frame length");
            ByteBuffer body = ByteBuffer.allocate(length);
            readFully(body);
            byte[] payload = body.array();
            CRC32 crc = new CRC32();
            crc.update(payload);
            if ((int)crc.getValue() != checksum) throw new IOException("pickup frame corrupted");
            try (DataInputStream in = new DataInputStream(new ByteArrayInputStream(payload))) {
                long number = in.readLong();
                byte[] prev = new byte[32];
                in.readFully(prev);
                if (number != sequence || !Arrays.equals(prev, previous))
                    throw new IOException("pickup chain or sequence mismatch");
                byte type = in.readByte();
                UUID job = new UUID(in.readLong(), in.readLong());
                if (type == 1) {
                    Intent intent = new Intent(world, job,
                        new UUID(in.readLong(), in.readLong()), in.readUTF(), in.readUTF(),
                        in.readLong(), in.readLong());
                    if (entries.putIfAbsent(job, new Entry(intent)) != null)
                        throw new IOException("duplicate extraction intent");
                } else if (type == 2 || type == 3) {
                    Entry entry = entries.get(job);
                    if (entry == null || entry.state != State.UNRESOLVED)
                        throw new IOException("orphan or repeated pickup outcome");
                    entry.state = type == 2 ? State.EXTRACTION_EMPTY : State.CARGO_RETURNED;
                } else if (type == 4) {
                    Entry entry = entries.get(job);
                    String destination = in.readUTF();
                    long tick = in.readLong();
                    if (entry == null || entry.state != State.CARGO_RETURNED
                            || entry.delivery != DeliveryState.NOT_STARTED
                            || destination.isBlank() || destination.length() > 512
                            || tick < entry.intent.attemptedTick())
                        throw new IOException("invalid or repeated delivery intent");
                    entry.destination = destination;
                    entry.deliveryTick = tick;
                    entry.delivery = DeliveryState.INSERTION_UNRESOLVED;
                } else if (type == 5) {
                    Entry entry = entries.get(job);
                    if (entry == null || entry.delivery != DeliveryState.INSERTION_UNRESOLVED)
                        throw new IOException("orphan or repeated delivery return");
                    entry.delivery = DeliveryState.INSERTION_RETURNED;
                } else throw new IOException("unknown pickup frame");
                if (in.available() != 0) throw new IOException("trailing pickup bytes");
            } catch (IllegalArgumentException ex) {
                throw new IOException("malformed pickup record", ex);
            }
            previous = hash(payload);
            sequence++;
        }
        channel.position(channel.size());
    }

    private static byte[] hash(byte[] bytes) {
        try { return MessageDigest.getInstance("SHA-256").digest(bytes); }
        catch (NoSuchAlgorithmException e) { throw new AssertionError(e); }
    }
    private void readFully(ByteBuffer bytes) throws IOException {
        while (bytes.hasRemaining()) if (channel.read(bytes) < 0)
            throw new IOException("torn pickup frame");
    }
    private void writeFully(ByteBuffer bytes) throws IOException {
        while (bytes.hasRemaining()) channel.write(bytes);
    }
    private void healthy() {
        if (closed || poisoned) throw new IllegalStateException("pickup journal unavailable");
    }
    @Override public synchronized void close() throws IOException {
        if (closed) return;
        closed = true;
        try { lock.release(); } finally { channel.close(); }
    }
}
