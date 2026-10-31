package dev.hearthbound.research;

import java.io.IOException;
import java.nio.file.*;
import java.util.concurrent.TimeUnit;
import dev.hearthbound.research.DurableOperationIntents.*;

public final class DurableOperationIntentsTest {
    private static final String KEY = "world-uuid/overworld/1,64,2/machine-incarnation";
    private static final String EVIDENCE = "{Input:{id:\"minecraft:wheat\",Count:1b,tag:{Custom:\"preserved\"}},Outputs:[]}";
    private static int checks;
    private interface Checked { void run() throws Exception; }
    private static void check(boolean value, String reason) {
        if (!value) throw new AssertionError(reason);
        checks++;
    }
    private static void rejects(Checked action) throws Exception {
        try { action.run(); } catch (IOException expected) { checks++; return; }
        throw new AssertionError("Invalid intent accepted");
    }
    private static Process child(Path path, String mode) throws IOException {
        return new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin", "java").toString(),
                "-cp", System.getProperty("java.class.path"), DurableOperationIntentsTest.class.getName(),
                path.toString(), mode).inheritIO().start();
    }
    private static void finish(Process process, int code) throws Exception {
        if (!process.waitFor(20, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            throw new AssertionError("Child timed out");
        }
        check(process.exitValue() == code, "Child exit code");
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 2) {
            Path directory = Path.of(args[0]);
            if (args[1].startsWith("writer")) {
                Intent intent = new DurableOperationIntents(directory).prepare(KEY, EVIDENCE).intent();
                Files.writeString(directory.resolve(args[1]), intent.operationId().toString());
            } else {
                new DurableOperationIntents(directory, phase -> {
                    if (phase.name().equals(args[1])) Runtime.getRuntime().halt(73);
                }).prepare(KEY, EVIDENCE);
            }
            return;
        }
        Path root = Files.createTempDirectory("hearthbound-intents-");
        Path normal = Files.createDirectory(root.resolve("normal"));
        DurableOperationIntents store = new DurableOperationIntents(normal);
        check(store.pending(KEY).isEmpty(), "Missing intent");
        Prepared initial = store.prepare(KEY, EVIDENCE);
        check(initial.newlyCreated(), "New intent permits first attempt only");
        Intent first = initial.intent();
        check(new DurableOperationIntents(normal).pending(KEY).orElseThrow().equals(first), "Reload full intent");
        Prepared retry = new DurableOperationIntents(normal).prepare(KEY, EVIDENCE);
        check(!retry.newlyCreated() && retry.intent().equals(first), "Existing intent requires reconciliation");
        rejects(() -> store.prepare(KEY, EVIDENCE + "changed"));
        check(store.pending(KEY).orElseThrow().equals(first), "Conflict preserves evidence");
        check(!store.prepare(KEY + "/replacement", EVIDENCE).intent().operationId().equals(first.operationId()),
                "Different machine incarnation gets distinct ID");

        for (Phase phase : Phase.values()) {
            Path directory = Files.createDirectory(root.resolve(phase.name()));
            finish(child(directory, phase.name()), 73);
            DurableOperationIntents reopened = new DurableOperationIntents(directory);
            if (phase == Phase.STAGED) {
                check(reopened.pending(KEY).isEmpty(), "Unpublished staging file cannot authorize mutation");
                check(reopened.prepare(KEY, EVIDENCE).intent().evidence().equals(EVIDENCE), "Retry after unpublished write");
            } else {
                Intent pending = reopened.pending(KEY).orElseThrow();
                check(pending.evidence().equals(EVIDENCE), "Published full evidence survives process exit");
                Prepared recovered = reopened.prepare(KEY, EVIDENCE);
                check(!recovered.newlyCreated() && recovered.intent().equals(pending), "Published ID requires reconciliation after lost acknowledgement");
            }
        }
        Path concurrent = Files.createDirectory(root.resolve("concurrent"));
        Process a = child(concurrent, "writer-a");
        Process b = child(concurrent, "writer-b");
        finish(a, 0);
        finish(b, 0);
        check(Files.readString(concurrent.resolve("writer-a")).equals(Files.readString(concurrent.resolve("writer-b"))),
                "Concurrent preparers receive one durable ID");
        Path corrupt = Files.createDirectory(root.resolve("corrupt"));
        DurableOperationIntents broken = new DurableOperationIntents(corrupt);
        broken.prepare(KEY, EVIDENCE);
        Path intentFile;
        try (var files = Files.list(corrupt)) {
            intentFile = files.filter(p -> p.toString().endsWith(".intent")).findFirst().orElseThrow();
        }
        byte[] bytes = Files.readAllBytes(intentFile);
        bytes[bytes.length - 1] ^= 1;
        Files.write(intentFile, bytes);
        rejects(() -> broken.pending(KEY));
        rejects(() -> broken.prepare(KEY, EVIDENCE));
        Files.write(intentFile, new byte[]{1, 2});
        rejects(() -> broken.pending(KEY));
        rejects(() -> broken.prepare(KEY, EVIDENCE));
        System.out.println("DurableOperationIntents: " + checks + " checks passed (5 child JVMs)");
    }
}
