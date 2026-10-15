package dev.hearthbound.jobs;

import java.util.Random;

/** Reproducible randomized state-machine checks. No dependencies or Minecraft runtime. */
public final class TransferLedgerPropertySmokeTest {
    private static void verify(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        Random random = new Random(0x4ea2b19L);
        for (int trial = 0; trial < 20_000; trial++) {
            TransferLedger ledger = new TransferLedger("trial-" + trial,
                    "minecraft:wheat", random.nextInt(64) + 1);
            int withdrawals = 0;
            int deliveries = 0;
            boolean cancelled = false;
            for (int step = 0; step < 20; step++) {
                TransferLedger.Phase before = ledger.phase();
                int operation = random.nextInt(3);
                boolean applied = switch (operation) {
                    case 0 -> ledger.withdraw();
                    case 1 -> ledger.deliver();
                    default -> ledger.cancel();
                };
                if (applied) {
                    switch (operation) {
                        case 0 -> { verify(before == TransferLedger.Phase.PLANNED, "illegal withdrawal"); withdrawals++; }
                        case 1 -> { verify(before == TransferLedger.Phase.WITHDRAWN, "illegal delivery"); deliveries++; }
                        default -> { verify(before == TransferLedger.Phase.PLANNED, "illegal cancel"); cancelled = true; }
                    }
                } else verify(ledger.phase() == before, "rejected operation mutated state");
                verify(withdrawals <= 1, "duplicate withdrawal");
                verify(deliveries <= withdrawals, "delivery without withdrawal");
                verify(deliveries <= 1, "duplicate delivery");
                verify(!cancelled || withdrawals == 0, "cancelled active cargo");
            }
            TransferLedger.Phase phase = ledger.phase();
            verify((phase != TransferLedger.Phase.DELIVERED || deliveries == 1)
                    && (phase != TransferLedger.Phase.CANCELLED || cancelled), "inconsistent terminal state");
        }
        System.out.println("PASS: 20,000 deterministic randomized transfer sequences");
    }
}
