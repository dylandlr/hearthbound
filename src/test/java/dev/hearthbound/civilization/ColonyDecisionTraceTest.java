package dev.hearthbound.civilization;

import java.util.UUID;
import dev.hearthbound.civilization.ColonyDecisionTrace.Trace;

public final class ColonyDecisionTraceTest {
    private static int checks;
    private static void ok(boolean yes, String name) {
        checks++;
        if (!yes) throw new AssertionError(name);
    }
    private static final UUID EPISODE = new UUID(1L, 1L);
    private static Trace trace(long revision, long observed, long decision,
                               long assigned, long delivered, UUID episode,
                               String action, String policy) {
        return new Trace(1L, new UUID(2L, 1L), new UUID(3L, 1L), episode,
            new UUID(4L, 1L), new UUID(5L, 1L), revision,
            observed, decision, assigned, delivered, action,
            "minecraft:overworld|4,100,1", policy);
    }
    public static void main(String[] args) {
        Trace base = trace(3, 10, 12, 15, 25, EPISODE, "GATHER",
                           "DETERMINISTIC_TRAIT_RANK_V1");
        ok(ColonyDecisionTrace.valid(base, EPISODE, 30), "valid bound job");
        ok(!ColonyDecisionTrace.valid(base, new UUID(9L, 9L), 30), "foreign episode");
        ok(!ColonyDecisionTrace.valid(base, EPISODE, 20), "undelivered future");
        ok(!ColonyDecisionTrace.valid(trace(0,10,12,15,25,EPISODE,"GATHER",
            "DETERMINISTIC_TRAIT_RANK_V1"), EPISODE, 30), "revision missing");
        ok(!ColonyDecisionTrace.valid(trace(3,10,9,15,25,EPISODE,"GATHER",
            "DETERMINISTIC_TRAIT_RANK_V1"), EPISODE, 30), "decision before evidence");
        ok(!ColonyDecisionTrace.valid(trace(3,10,16,15,25,EPISODE,"GATHER",
            "DETERMINISTIC_TRAIT_RANK_V1"), EPISODE, 30), "decision after assignment");
        ok(!ColonyDecisionTrace.valid(trace(3,10,12,15,14,EPISODE,"GATHER",
            "DETERMINISTIC_TRAIT_RANK_V1"), EPISODE, 30), "delivery before assignment");
        ok(!ColonyDecisionTrace.valid(trace(3,10,12,31,35,EPISODE,"GATHER",
            "DETERMINISTIC_TRAIT_RANK_V1"), EPISODE, 40), "stale evidence");
        ok(!ColonyDecisionTrace.valid(trace(3,10,12,15,25,EPISODE,"WAIT",
            "DETERMINISTIC_TRAIT_RANK_V1"), EPISODE, 30), "wrong action");
        ok(!ColonyDecisionTrace.valid(trace(3,10,12,15,25,EPISODE,"GATHER",
            "UNVERIFIED_NEURAL"), EPISODE, 30), "wrong policy");
        ok(ColonyDecisionTrace.encode(base).split(",").length == 10, "ten fixed fields");
        System.out.println("PASS " + checks + " pure citizen decision trace checks");
    }
}
