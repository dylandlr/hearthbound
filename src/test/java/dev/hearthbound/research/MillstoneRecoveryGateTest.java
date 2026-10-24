package dev.hearthbound.research;

import java.util.List;
import java.util.UUID;
import dev.hearthbound.research.MillstoneReceiptGate.*;
import dev.hearthbound.research.MillstoneRecoveryGate.*;

public final class MillstoneRecoveryGateTest {
    private static int checks;
    private static void check(boolean value, String message) {
        if (!value) throw new AssertionError(message);
        checks++;
    }
    public static void main(String[] args) {
        UUID id = UUID.fromString("00000000-0000-0000-0000-000000000001");
        InputProof proof = new InputProof(id, "world", "minecraft:overworld", "1,64,2",
                "create:milling/wheat", List.of(new Stack("minecraft:wheat", 1)));
        Completion completion = new Completion("MILLSTONE", id, "world", "minecraft:overworld",
                "1,64,2", "create:milling/wheat", List.of(new Stack("create:wheat_flour", 1)));
        // Every partial checkpoint combination must fail closed, including a
        // credit entry surviving while the corresponding operation files do not.
        for (CreditState credit : CreditState.values()) {
            for (int presence = 0; presence < 3; presence++) {
                Result result = MillstoneRecoveryGate.recover(
                        (presence & 1) != 0 ? proof : null,
                        (presence & 2) != 0 ? completion : null, credit);
                check(result.decision() == Decision.QUARANTINE && result.receipt() == null,
                        "Partial checkpoint must not grant credit: " + presence + "/" + credit);
            }
        }
        for (CreditState credit : CreditState.values()) {
            Completion wrongId = new Completion("MILLSTONE", UUID.randomUUID(), "world",
                    "minecraft:overworld", "1,64,2", "create:milling/wheat", completion.produced());
            Result result = MillstoneRecoveryGate.recover(proof, wrongId, credit);
            check(result.decision() == Decision.QUARANTINE && result.receipt() == null,
                    "Conflicting operation must not grant credit");
        }
        Result ready = MillstoneRecoveryGate.recover(proof, completion, CreditState.ABSENT);
        check(ready.decision() == Decision.READY_FOR_ATOMIC_CREDIT, "Complete uncredited evidence");
        check(ready.receipt().operationId().equals(id), "Preserve durable operation ID");
        check(ready.receipt().consumed().equals(proof.consumed()), "Preserve inputs");
        check(ready.receipt().produced().equals(completion.produced()), "Preserve outputs");
        for (int replay = 0; replay < 10; replay++) {
            Result duplicate = MillstoneRecoveryGate.recover(proof, completion, CreditState.MATCHING);
            check(duplicate.decision() == Decision.ALREADY_CREDITED && duplicate.receipt() == null,
                    "Repeated recovery cannot produce another credit candidate");
        }
        for (CreditState credit : List.of(CreditState.UNKNOWN, CreditState.CONFLICTING)) {
            Result blocked = MillstoneRecoveryGate.recover(proof, completion, credit);
            check(blocked.decision() == Decision.QUARANTINE && blocked.receipt() == null,
                    "Uncertain credit state must fail closed");
        }
        System.out.println("MillstoneRecoveryGate: " + checks + " checks passed");
    }
}
