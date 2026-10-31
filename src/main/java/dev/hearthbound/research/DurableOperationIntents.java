package dev.hearthbound.research;

import java.io.*;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.*;
import java.security.*;
import java.util.*;
import java.util.function.Consumer;
import static java.nio.file.StandardOpenOption.*;

/**
 * One unresolved pre-operation intent per stable machine key. Not wired to Create.
 * Callers may mutate only after prepare returns, and must reconcile before retiring
 * an intent. Deliberately no delete/complete API until machine checkpointing exists.
 */
public final class DurableOperationIntents {
    private static final int MAGIC = 0x48424931;
    private final Path directory;
    enum Phase { STAGED, PUBLISHED, FORCED }
    private final Consumer<Phase> checkpoint;
    public record Intent(UUID operationId, String machineKey, String evidence) {
        public Intent {
            Objects.requireNonNull(operationId);
            validate(machineKey, evidence);
        }
    }
    public record Prepared(Intent intent, boolean newlyCreated) {}
    public DurableOperationIntents(Path directory) { this(directory, phase -> {}); }
    DurableOperationIntents(Path directory, Consumer<Phase> checkpoint) {
        this.directory = directory.toAbsolutePath();
        this.checkpoint = Objects.requireNonNull(checkpoint);
    }

    /**
     * machineKey includes stable world, dimension, position and machine incarnation.
     * evidence is a deterministic full snapshot supplied by the adapter, not a hash.
     * Reuse means an unresolved intent was found, NOT permission to replay a mutation.
     */
    public synchronized Prepared prepare(String machineKey, String evidence) throws IOException {
        validate(machineKey, evidence);
        Path target = target(machineKey);
        try (FileChannel lock = FileChannel.open(directory.resolve("intents.lock"), CREATE, WRITE);
             var held = lock.lock()) {
            Intent existing = readIfPresent(target);
            if (existing != null) {
                if (!existing.machineKey().equals(machineKey) || !existing.evidence().equals(evidence))
                    throw new IOException("Unresolved intent conflicts with machine evidence");
                forceFile(target);
                forceDirectory();
                return new Prepared(existing, false);
            }
            Intent intent = new Intent(UUID.randomUUID(), machineKey, evidence);
            byte[] body = encode(intent);
            Path staged = Files.createTempFile(directory, "intent-", ".pending");
            try {
                try (FileChannel file = FileChannel.open(staged, WRITE)) {
                    write(file, ByteBuffer.wrap(body));
                    write(file, ByteBuffer.wrap(hash(body)));
                    file.force(true);
                }
                checkpoint.accept(Phase.STAGED);
                Files.move(staged, target, StandardCopyOption.ATOMIC_MOVE);
                checkpoint.accept(Phase.PUBLISHED);
                forceDirectory();
                checkpoint.accept(Phase.FORCED);
                return new Prepared(intent, true);
            } finally { Files.deleteIfExists(staged); }
        }
    }
    /** Missing is distinct from corrupt; corrupt or unreadable intents throw. */
    public synchronized Optional<Intent> pending(String machineKey) throws IOException {
        validate(machineKey, "lookup");
        try (FileChannel lock = FileChannel.open(directory.resolve("intents.lock"), CREATE, WRITE);
             var held = lock.lock()) {
            Intent intent = readIfPresent(target(machineKey));
            if (intent != null && !intent.machineKey().equals(machineKey))
                throw new IOException("Intent machine key mismatch");
            return Optional.ofNullable(intent);
        }
    }
    private Path target(String key) {
        return directory.resolve(HexFormat.of().formatHex(hash(key.getBytes(java.nio.charset.StandardCharsets.UTF_8))) + ".intent");
    }
    private static Intent readIfPresent(Path path) throws IOException {
        byte[] bytes;
        try (FileChannel file = FileChannel.open(path, READ)) {
            long size = file.size();
            if (size < 33 || size > 65536) throw new IOException("Invalid intent size");
            ByteBuffer buffer = ByteBuffer.allocate((int) size);
            while (buffer.hasRemaining())
                if (file.read(buffer) < 0) throw new EOFException("Torn intent");
            bytes = buffer.array();
        } catch (NoSuchFileException absent) { return null; }
        byte[] body = Arrays.copyOf(bytes, bytes.length - 32);
        if (!MessageDigest.isEqual(hash(body), Arrays.copyOfRange(bytes, body.length, bytes.length)))
            throw new IOException("Corrupt intent");
        try (DataInputStream in = new DataInputStream(new ByteArrayInputStream(body))) {
            if (in.readInt() != MAGIC) throw new IOException("Invalid intent version");
            Intent intent = new Intent(UUID.fromString(in.readUTF()), in.readUTF(), in.readUTF());
            if (in.available() != 0) throw new IOException("Trailing intent data");
            return intent;
        } catch (IllegalArgumentException invalid) { throw new IOException("Invalid intent", invalid); }
    }
    private static byte[] encode(Intent intent) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream out = new DataOutputStream(bytes)) {
            out.writeInt(MAGIC);
            out.writeUTF(intent.operationId().toString());
            out.writeUTF(intent.machineKey());
            out.writeUTF(intent.evidence());
        }
        return bytes.toByteArray();
    }
    private static void validate(String key, String evidence) {
        if (key == null || key.isBlank() || key.length() > 1000
                || evidence == null || evidence.isBlank() || evidence.length() > 16000)
            throw new IllegalArgumentException("Invalid machine key or full evidence");
    }
    private void forceDirectory() throws IOException {
        try (FileChannel dir = FileChannel.open(directory, READ)) { dir.force(true); }
    }
    private static void forceFile(Path path) throws IOException {
        try (FileChannel file = FileChannel.open(path, WRITE)) { file.force(true); }
    }
    private static void write(FileChannel file, ByteBuffer bytes) throws IOException {
        while (bytes.hasRemaining()) file.write(bytes);
    }
    private static byte[] hash(byte[] bytes) {
        try { return MessageDigest.getInstance("SHA-256").digest(bytes); }
        catch (NoSuchAlgorithmException impossible) { throw new AssertionError(impossible); }
    }
}
