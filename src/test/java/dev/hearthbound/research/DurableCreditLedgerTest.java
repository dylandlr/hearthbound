package dev.hearthbound.research;

import java.io.IOException;
import java.nio.file.*;
import java.util.UUID;
import java.util.concurrent.TimeUnit;
import dev.hearthbound.research.DurableCreditLedger.*;

public final class DurableCreditLedgerTest {
    private static final UUID ACCOUNT = new UUID(0, 10);
    private static final Credit FIRST = new Credit(new UUID(0, 1), ACCOUNT, 7, "validated-receipt-one");
    private static final Credit SECOND = new Credit(new UUID(0, 2), ACCOUNT, 11, "validated-receipt-two");
    private static int checks;
    private interface Checked { void run() throws Exception; }
    private static void check(boolean condition, String label) {
        if (!condition) throw new AssertionError(label);
        checks++;
    }
    private static void rejects(Checked action) throws Exception {
        try { action.run(); } catch (IOException expected) { checks++; return; }
        throw new AssertionError("Unsafe ledger operation accepted");
    }
    private static Process child(Path path, String mode) throws IOException {
        return new ProcessBuilder(Path.of(System.getProperty("java.home"), "bin", "java").toString(),
                "-cp", System.getProperty("java.class.path"), DurableCreditLedgerTest.class.getName(),
                path.toString(), mode).inheritIO().start();
    }
    private static void finish(Process process, int expected) throws Exception {
        if (!process.waitFor(20, TimeUnit.SECONDS)) {
            process.destroyForcibly();
            throw new AssertionError("Child JVM timed out");
        }
        check(process.exitValue() == expected, "Child exit status");
    }
    public static void main(String[] args) throws Exception {
        if (args.length == 2) {
            Path path = Path.of(args[0]);
            if (args[1].equals("commit")) new DurableCreditLedger(path).commit(SECOND);
            else new DurableCreditLedger(path, phase -> {
                if (phase.name().equals(args[1])) Runtime.getRuntime().halt(73);
            }).commit(SECOND);
            return;
        }
        Path root = Files.createTempDirectory("hearthbound-credit-tests-");
        Path normal = Files.createDirectory(root.resolve("normal"));
        DurableCreditLedger ledger = new DurableCreditLedger(normal);
        check(ledger.balance(ACCOUNT) == 0, "Empty balance");
        check(ledger.commit(FIRST), "First commit");
        check(!new DurableCreditLedger(normal).commit(FIRST), "Reopened duplicate rejected");
        check(ledger.balance(ACCOUNT) == 7, "Duplicate leaves balance unchanged");
        rejects(() -> ledger.commit(new Credit(FIRST.operationId(), ACCOUNT, 8, FIRST.receipt())));
        rejects(() -> ledger.commit(new Credit(FIRST.operationId(), new UUID(0, 99), 7, FIRST.receipt())));
        rejects(() -> ledger.commit(new Credit(FIRST.operationId(), ACCOUNT, 7, "different-receipt")));
        check(ledger.balance(ACCOUNT) == 7, "Conflicts leave balance unchanged");

        for (Phase phase : Phase.values()) {
            Path directory = Files.createDirectory(root.resolve(phase.name()));
            new DurableCreditLedger(directory).commit(FIRST);
            finish(child(directory, phase.name()), 73);
            DurableCreditLedger reopened = new DurableCreditLedger(directory);
            if (phase == Phase.FORCED) {
                check(reopened.balance(ACCOUNT) == 18, "Forced reward survives abrupt process exit");
                check(!reopened.commit(SECOND), "Retry after lost acknowledgement cannot double credit");
                check(reopened.balance(ACCOUNT) == 18, "Retry balance");
            } else {
                rejects(() -> reopened.balance(ACCOUNT));
                rejects(() -> reopened.commit(SECOND));
                rejects(() -> reopened.commit(FIRST));
            }
        }

        Path concurrent = Files.createDirectory(root.resolve("concurrent"));
        new DurableCreditLedger(concurrent).commit(FIRST);
        Process a = child(concurrent, "commit");
        Process b = child(concurrent, "commit");
        finish(a, 0);
        finish(b, 0);
        check(new DurableCreditLedger(concurrent).balance(ACCOUNT) == 18,
                "Two JVMs credit the same operation only once");

        Path corrupted = Files.createDirectory(root.resolve("corrupted"));
        new DurableCreditLedger(corrupted).commit(FIRST);
        Path file = corrupted.resolve("credits.v1");
        byte[] bytes = Files.readAllBytes(file);
        bytes[bytes.length - 1] ^= 1;
        Files.write(file, bytes);
        rejects(() -> new DurableCreditLedger(corrupted).balance(ACCOUNT));
        rejects(() -> new DurableCreditLedger(corrupted).commit(SECOND));

        Path overflow = Files.createDirectory(root.resolve("overflow"));
        DurableCreditLedger maximum = new DurableCreditLedger(overflow);
        maximum.commit(new Credit(FIRST.operationId(), ACCOUNT, Long.MAX_VALUE, FIRST.receipt()));
        rejects(() -> maximum.commit(SECOND));
        check(maximum.balance(ACCOUNT) == Long.MAX_VALUE, "Overflow does not append");
        System.out.println("DurableCreditLedger: " + checks + " checks passed (5 child JVMs)");
    }
}
