package dev.hearthbound.research;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.*;
import java.util.function.Consumer;
import static java.nio.file.StandardOpenOption.*;

/**
 * Append-only credit ledger. The complete receipt and reward are one checksummed
 * frame; balances are derived from frames, never written to a separate file.
 * A torn/corrupt frame blocks ALL reads and writes pending explicit reconciliation.
 * Storage only: callers must validate authoritative evidence before committing.
 */
public final class DurableCreditLedger {
    private static final int MAGIC = 0x48424331;
    private static final int MAX_FRAME = 65536;
    private final Path directory;
    enum Phase { HEADER_WRITTEN, PAYLOAD_WRITTEN, FORCED }
    private final Consumer<Phase> checkpoint;

    public record Credit(UUID operationId, UUID beneficiary, long amount, String receipt) {
        public Credit {
            Objects.requireNonNull(operationId);
            Objects.requireNonNull(beneficiary);
            if (amount <= 0 || receipt == null || receipt.isBlank() || receipt.length() > 16000)
                throw new IllegalArgumentException("Invalid credit");
        }
    }

    /** Directory must already exist on a filesystem supporting locks and directory force. */
    public DurableCreditLedger(Path directory) {
        this(directory, phase -> {});
    }
    DurableCreditLedger(Path directory, Consumer<Phase> checkpoint) {
        this.directory = directory.toAbsolutePath();
        this.checkpoint = Objects.requireNonNull(checkpoint);
    }

    public synchronized boolean commit(Credit credit) throws IOException {
        Objects.requireNonNull(credit);
        try (FileChannel lock = FileChannel.open(directory.resolve("credit.lock"), CREATE, WRITE);
             var held = lock.lock();
             FileChannel data = FileChannel.open(directory.resolve("credits.v1"), CREATE, READ, WRITE)) {
            // Also force the directory on retry, including after an uncertain initial commit.
            forceDirectory();
            Map<UUID, Credit> credits = read(data);
            Credit existing = credits.get(credit.operationId());
            if (existing != null) {
                if (!existing.equals(credit)) throw new IOException("Conflicting operation credit");
                data.force(true);
                return false;
            }
            try { Math.addExact(balance(credits.values(), credit.beneficiary()), credit.amount()); }
            catch (ArithmeticException overflow) { throw new IOException("Balance overflow", overflow); }
            byte[] payload = encode(credit);
            data.position(data.size());
            write(data, ByteBuffer.allocate(8).putInt(MAGIC).putInt(payload.length).flip());
            checkpoint.accept(Phase.HEADER_WRITTEN);
            write(data, ByteBuffer.wrap(payload));
            checkpoint.accept(Phase.PAYLOAD_WRITTEN);
            write(data, ByteBuffer.wrap(hash(payload)));
            data.force(true);
            checkpoint.accept(Phase.FORCED);
            return true;
        }
    }

    public synchronized long balance(UUID beneficiary) throws IOException {
        Objects.requireNonNull(beneficiary);
        try (FileChannel lock = FileChannel.open(directory.resolve("credit.lock"), CREATE, WRITE);
             var held = lock.lock()) {
            Path file = directory.resolve("credits.v1");
            try (FileChannel data = FileChannel.open(file, READ)) {
                try { return balance(read(data).values(), beneficiary); }
                catch (ArithmeticException overflow) { throw new IOException("Balance overflow", overflow); }
            } catch (NoSuchFileException absent) { return 0; }
        }
    }

    private void forceDirectory() throws IOException {
        try (FileChannel dir = FileChannel.open(directory, READ)) { dir.force(true); }
    }
    private static long balance(Collection<Credit> credits, UUID beneficiary) {
        long value = 0;
        for (Credit credit : credits)
            if (credit.beneficiary().equals(beneficiary)) value = Math.addExact(value, credit.amount());
        return value;
    }
    private static Map<UUID, Credit> read(FileChannel data) throws IOException {
        Map<UUID, Credit> result = new LinkedHashMap<>();
        data.position(0);
        while (data.position() < data.size()) {
            ByteBuffer header = ByteBuffer.allocate(8);
            readFully(data, header);
            header.flip();
            if (header.getInt() != MAGIC) throw new IOException("Invalid credit frame version");
            int size = header.getInt();
            if (size <= 0 || size > MAX_FRAME) throw new IOException("Invalid credit frame size");
            ByteBuffer body = ByteBuffer.allocate(size + 32);
            readFully(data, body);
            byte[] payload = Arrays.copyOfRange(body.array(), 0, size);
            byte[] digest = Arrays.copyOfRange(body.array(), size, size + 32);
            if (!MessageDigest.isEqual(hash(payload), digest)) throw new IOException("Corrupt credit frame");
            Credit credit = decode(payload);
            if (result.putIfAbsent(credit.operationId(), credit) != null)
                throw new IOException("Duplicate persisted credit");
        }
        return result;
    }
    private static byte[] encode(Credit credit) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(bytes)) {
            out.writeUTF(credit.operationId().toString());
            out.writeUTF(credit.beneficiary().toString());
            out.writeLong(credit.amount());
            out.writeUTF(credit.receipt());
        }
        return bytes.toByteArray();
    }
    private static Credit decode(byte[] bytes) throws IOException {
        try (DataInputStream in = new DataInputStream(new ByteArrayInputStream(bytes))) {
            Credit credit = new Credit(UUID.fromString(in.readUTF()), UUID.fromString(in.readUTF()),
                    in.readLong(), in.readUTF());
            if (in.available() != 0) throw new IOException("Trailing credit data");
            return credit;
        } catch (IllegalArgumentException invalid) { throw new IOException("Invalid persisted credit", invalid); }
    }
    private static byte[] hash(byte[] bytes) {
        try { return MessageDigest.getInstance("SHA-256").digest(bytes); }
        catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
    private static void write(FileChannel channel, ByteBuffer bytes) throws IOException {
        while (bytes.hasRemaining()) channel.write(bytes);
    }
    private static void readFully(FileChannel channel, ByteBuffer bytes) throws IOException {
        while (bytes.hasRemaining())
            if (channel.read(bytes) < 0) throw new EOFException("Torn credit frame; reconciliation required");
    }
}
