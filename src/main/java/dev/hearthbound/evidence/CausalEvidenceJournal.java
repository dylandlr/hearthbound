package dev.hearthbound.evidence;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.UUID;
import java.util.zip.CRC32;

/**
 * Read-only-for-learning, single-writer causal EVIDENCE journal. An ADMITTED
 * record is an audit state, NEVER an authorization to pay or train an agent.
 *
 * Replay cannot restore active admission: after EVERY reopen ADMITTED entries
 * require independent, current Minecraft source revalidation.
 *
 * Framing is fail-closed: magic/version/world UUID header, contiguous sequence,
 * chained SHA-256 payload digests and per-frame CRC32. Corrupt or torn frames
 * abort opening; no speculative repair or automatic truncation is attempted.
 */
public final class CausalEvidenceJournal implements AutoCloseable {
    private static final int MAGIC = 0x4842434a; // HBCJ
    private static final int VERSION = 1;
    private static final int HEADER_BYTES = 28;
    private static final int MAX_FRAME = 65536;
    private static final byte OBSERVE = 1, ADMIT = 2, REVOKE = 3;

    public enum State { OBSERVED, ADMITTED, REVOKED }

    public record Observation(UUID world, String eventId, String physicalEvidenceId,
                              String jobId, String citizenId, String dimension,
                              long machinePos, long assignedTick, long startTick,
                              long finishTick) {
        public Observation {
            Objects.requireNonNull(world, "world");
            requireText(jobId);
            requireText(citizenId);
            requireText(dimension);
            requireText(eventId);
            requireText(physicalEvidenceId);
            if (!UUID.fromString(jobId).toString().equals(jobId)
                    || !UUID.fromString(citizenId).toString().equals(citizenId)
                    || assignedTick < 0 || startTick < assignedTick
                    || finishTick <= startTick)
                throw new IllegalArgumentException("invalid Minecraft chronology or identity");
            String event = "hearthbound:mill:v1:" + world + ":" + dimension + ":" + jobId;
            String physical = "hearthbound:create-process:v1:" + world + ":"
                + dimension + ":" + machinePos + ":" + jobId + ":" + startTick
                + ":" + finishTick;
            if (!event.equals(eventId) || !physical.equals(physicalEvidenceId))
                throw new IllegalArgumentException("noncanonical event or process identity");
        }
    }

    public record View(Observation observation, State state,
                       boolean revalidatedThisSession, String revocationReason) {
        public boolean activeForAudit() {
            return state == State.ADMITTED && revalidatedThisSession;
        }
    }

    @FunctionalInterface
    public interface CurrentSource {
        /** Called ONLY after game-side checks confirm citizen/machine are loaded. */
        boolean matches(Observation expected) throws Exception;
    }

    private static final class Entry {
        final Observation observation;
        State state = State.OBSERVED;
        boolean current;
        String reason = "";
        Entry(Observation observation) { this.observation = observation; }
        View snapshot() { return new View(observation, state, current, reason); }
    }

    private final UUID world;
    private final FileChannel file;
    private final FileLock lock;
    private final Map<String, Entry> known = new LinkedHashMap<>();
    private final Map<String, String> physicalOwner = new LinkedHashMap<>();
    private byte[] previousHash = new byte[32];
    private long nextSequence = 1;
    private boolean poisoned;
    private boolean closed;

    public CausalEvidenceJournal(Path path, UUID expectedWorld) throws IOException {
        Objects.requireNonNull(path);
        world = Objects.requireNonNull(expectedWorld);
        Path absolute = path.toAbsolutePath().normalize();
        if (absolute.getParent() == null) throw new IOException("missing journal parent");
        Files.createDirectories(absolute.getParent());
        file = FileChannel.open(absolute, StandardOpenOption.CREATE,
            StandardOpenOption.READ, StandardOpenOption.WRITE);
        FileLock acquired = null;
        try {
            try {
                acquired = file.tryLock();
            } catch (OverlappingFileLockException e) {
                throw new IOException("causal evidence journal already has a writer", e);
            }
            if (acquired == null) throw new IOException("causal evidence journal already locked");
            lock = acquired;
            recover();
            file.position(file.size());
        } catch (IOException | RuntimeException e) {
            if (acquired != null) {
                try { acquired.release(); } catch (IOException suppressed) { e.addSuppressed(suppressed); }
            }
            try { file.close(); } catch (IOException suppressed) { e.addSuppressed(suppressed); }
            throw e;
        }
    }

    public synchronized boolean observe(Observation observation) throws IOException {
        requireHealthy();
        Objects.requireNonNull(observation);
        if (!world.equals(observation.world())) throw new IOException("foreign world observation");
        Entry prior = known.get(observation.eventId());
        if (prior != null) {
            if (!prior.observation.equals(observation))
                throw new IOException("conflicting event replay");
            return false;
        }
        String owner = physicalOwner.get(observation.physicalEvidenceId());
        if (owner != null)
            throw new IOException("one Create processing callback assigned twice");
        append(OBSERVE, observation.eventId(), observation, "");
        install(observation);
        return true;
    }

    /**
     * A false, positively checked authoritative source match is a terminal
     * REVOKED outcome; uncertainty such as unloaded chunks must be rejected by
     * the caller BEFORE invoking this method.
     */
    public synchronized View reconcile(String eventId, CurrentSource source) throws Exception {
        requireHealthy();
        Entry entry = requireEntry(eventId);
        if (entry.state == State.REVOKED) return entry.snapshot();
        entry.current = false;
        boolean matched = Objects.requireNonNull(source).matches(entry.observation);
        if (!matched) {
            revoke(eventId, "SOURCE_MISMATCH_OR_TAINT");
            return entry.snapshot();
        }
        if (entry.state == State.OBSERVED) {
            append(ADMIT, eventId, null, "");
            entry.state = State.ADMITTED;
        }
        // An ADMITTED record recovered from disk is NEVER trusted by itself.
        // A successful live source read is required on every process lifetime.
        entry.current = true;
        return entry.snapshot();
    }

    public synchronized boolean revoke(String eventId, String reason) throws IOException {
        requireHealthy();
        Entry entry = requireEntry(eventId);
        requireText(reason);
        if (entry.state == State.REVOKED) return false;
        append(REVOKE, eventId, null, reason);
        entry.state = State.REVOKED;
        entry.current = false;
        entry.reason = reason;
        return true;
    }

    public synchronized View inspect(String eventId) {
        requireHealthy();
        Entry entry = known.get(eventId);
        return entry == null ? null : entry.snapshot();
    }

    public synchronized int size() { requireHealthy(); return known.size(); }

    private Entry requireEntry(String eventId) {
        Entry found = known.get(eventId);
        if (found == null) throw new IllegalArgumentException("unknown causal evidence event");
        return found;
    }

    private void install(Observation observation) throws IOException {
        if (known.putIfAbsent(observation.eventId(), new Entry(observation)) != null)
            throw new IOException("duplicate observation frame");
        if (physicalOwner.putIfAbsent(observation.physicalEvidenceId(), observation.eventId()) != null)
            throw new IOException("duplicate physical process frame");
    }

    private void append(byte type, String eventId, Observation observation, String reason)
            throws IOException {
        byte[] payload = encode(nextSequence, previousHash, type, eventId, observation, reason);
        if (payload.length < 42 || payload.length > MAX_FRAME)
            throw new IOException("oversized causal evidence frame");
        CRC32 crc = new CRC32();
        crc.update(payload);
        ByteBuffer frame = ByteBuffer.allocate(payload.length + 8)
            .putInt(payload.length).putInt((int) crc.getValue()).put(payload);
        frame.flip();
        try {
            file.position(file.size());
            writeFully(frame);
            file.force(true);
        } catch (IOException | RuntimeException e) {
            poisoned = true; // Do not continue after a potentially torn fsync.
            throw e;
        }
        previousHash = sha256(payload);
        nextSequence++;
    }

    private void recover() throws IOException {
        long size = file.size();
        if (size == 0) {
            byte[] start = new byte[24];
            ByteBuffer data = ByteBuffer.wrap(start).putInt(MAGIC).putInt(VERSION)
                .putLong(world.getMostSignificantBits()).putLong(world.getLeastSignificantBits());
            CRC32 crc = new CRC32();
            crc.update(start);
            ByteBuffer header = ByteBuffer.allocate(HEADER_BYTES).put(start)
                .putInt((int) crc.getValue());
            header.flip();
            writeFully(header);
            file.force(true);
            return;
        }
        if (size < HEADER_BYTES) throw new IOException("truncated world-bound header");
        ByteBuffer header = ByteBuffer.allocate(HEADER_BYTES);
        if (!readFully(header)) throw new IOException("truncated header");
        header.flip();
        byte[] headerData = new byte[24];
        header.get(headerData);
        int checksum = header.getInt();
        CRC32 crc = new CRC32();
        crc.update(headerData);
        if ((int) crc.getValue() != checksum) throw new IOException("corrupt header checksum");
        ByteBuffer value = ByteBuffer.wrap(headerData);
        if (value.getInt() != MAGIC || value.getInt() != VERSION)
            throw new IOException("wrong journal magic/version");
        UUID encodedWorld = new UUID(value.getLong(), value.getLong());
        if (!world.equals(encodedWorld)) throw new IOException("foreign Minecraft world UUID");
        while (file.position() < file.size()) {
            ByteBuffer hdr = ByteBuffer.allocate(8);
            if (!readFully(hdr)) throw new IOException("torn causal evidence frame header");
            hdr.flip();
            int length = hdr.getInt();
            int expectedCrc = hdr.getInt();
            if (length < 42 || length > MAX_FRAME) throw new IOException("invalid frame size");
            ByteBuffer body = ByteBuffer.allocate(length);
            if (!readFully(body)) throw new IOException("torn causal evidence frame payload");
            byte[] payload = body.array();
            crc.reset();
            crc.update(payload);
            if ((int) crc.getValue() != expectedCrc)
                throw new IOException("corrupt causal evidence checksum");
            try (DataInputStream in = new DataInputStream(new ByteArrayInputStream(payload))) {
                long sequence = in.readLong();
                byte[] previous = new byte[32];
                in.readFully(previous);
                if (sequence != nextSequence || !Arrays.equals(previous, previousHash))
                    throw new IOException("broken hash chain or sequence");
                byte type = in.readByte();
                String eventId = in.readUTF();
                if (type == OBSERVE) {
                    Observation observation = decodeObservation(in);
                    if (!eventId.equals(observation.eventId()) || !world.equals(observation.world()))
                        throw new IOException("invalid observation world/event ID");
                    if (known.containsKey(eventId)
                            || physicalOwner.containsKey(observation.physicalEvidenceId()))
                        throw new IOException("replayed or reused observation");
                    install(observation);
                } else if (type == ADMIT) {
                    Entry entry = requireEntry(eventId);
                    if (entry.state != State.OBSERVED)
                        throw new IOException("invalid admission transition");
                    entry.state = State.ADMITTED;
                } else if (type == REVOKE) {
                    Entry entry = requireEntry(eventId);
                    if (entry.state == State.REVOKED)
                        throw new IOException("duplicate revocation frame");
                    String reason = in.readUTF();
                    requireText(reason);
                    entry.state = State.REVOKED;
                    entry.reason = reason;
                } else {
                    throw new IOException("unknown causal evidence frame");
                }
                if (in.available() != 0) throw new IOException("trailing frame bytes");
            } catch (IllegalArgumentException e) {
                throw new IOException("invalid causal evidence payload", e);
            }
            previousHash = sha256(payload);
            nextSequence++;
        }
        // Entry.current defaults to false, including replayed ADMITTED entries.
    }

    private Observation decodeObservation(DataInputStream in) throws IOException {
        try {
            return new Observation(world, in.readUTF(), in.readUTF(), in.readUTF(),
                in.readUTF(), in.readUTF(), in.readLong(), in.readLong(),
                in.readLong(), in.readLong());
        } catch (IllegalArgumentException e) {
            throw new IOException("bad recorded observation", e);
        }
    }

    private static byte[] encode(long sequence, byte[] previous, byte type,
                                 String eventId, Observation observation, String reason)
            throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(bytes)) {
            out.writeLong(sequence);
            out.write(previous);
            out.writeByte(type);
            out.writeUTF(eventId);
            if (type == OBSERVE) {
                out.writeUTF(observation.eventId());
                out.writeUTF(observation.physicalEvidenceId());
                out.writeUTF(observation.jobId());
                out.writeUTF(observation.citizenId());
                out.writeUTF(observation.dimension());
                out.writeLong(observation.machinePos());
                out.writeLong(observation.assignedTick());
                out.writeLong(observation.startTick());
                out.writeLong(observation.finishTick());
            } else if (type == REVOKE) {
                out.writeUTF(reason);
            }
        }
        return bytes.toByteArray();
    }

    private static byte[] sha256(byte[] bytes) {
        try {
            return MessageDigest.getInstance("SHA-256").digest(bytes);
        } catch (NoSuchAlgorithmException e) {
            throw new AssertionError("JVM missing SHA-256", e);
        }
    }

    private static void requireText(String text) {
        if (text == null || text.isBlank() || text.indexOf('\0') >= 0)
            throw new IllegalArgumentException("missing or unsafe evidence identifier");
    }

    private boolean readFully(ByteBuffer buffer) throws IOException {
        while (buffer.hasRemaining()) if (file.read(buffer) < 0) return false;
        return true;
    }

    private void writeFully(ByteBuffer buffer) throws IOException {
        while (buffer.hasRemaining()) file.write(buffer);
    }

    private void requireHealthy() {
        if (closed || poisoned) throw new IllegalStateException("journal closed or unsafe after write failure");
    }

    @Override
    public synchronized void close() throws IOException {
        if (closed) return;
        closed = true;
        try {
            lock.release();
        } finally {
            file.close();
        }
    }
}
