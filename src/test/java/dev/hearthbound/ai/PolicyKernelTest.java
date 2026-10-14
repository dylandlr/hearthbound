package dev.hearthbound.ai;

import java.util.List;
import static dev.hearthbound.ai.ColonyPolicy.*;

/** Dependency-free CI smoke and regression suite for the pure policy kernel. */
public final class PolicyKernelTest {
    private static void check(boolean assertion, String name) {
        if (!assertion) throw new AssertionError(name);
    }

    private static Observation observation(int danger, int hunger, int fatigue, Action... actions) {
        return new Observation(12L, "sable", hunger, danger, fatigue, List.of(actions));
    }

    public static void main(String[] args) {
        Action flee = new Action("flee", Kind.FLEE, 0, true);
        Action eat = new Action("eat", Kind.EAT, 0, true);
        Action haul = new Action("haul", Kind.HAUL, 0, true);
        Action blocked = new Action("operate", Kind.OPERATE, 9000, false);
        PriorityPolicy policy = new PriorityPolicy();

        Observation threatened = observation(95, 90, 90, flee, eat, haul);
        Decision choice = policy.choose(threatened);
        check(choice.actionId().equals("flee"), "danger overrides hunger");
        check(ActionGate.allowed(threatened, choice), "valid selection accepted");
        check(!ActionGate.allowed(threatened, new Decision(11, "flee", "stale")), "stale rejected");
        check(!ActionGate.allowed(threatened, new Decision(12, "spawn_items", "unlisted")), "unknown rejected");
        check(!ActionGate.allowed(observation(0, 0, 0, blocked), new Decision(12, "operate", "blocked")),
            "non-executable rejected");
        check(policy.choose(observation(0, 90, 0, eat, haul)).actionId().equals("eat"), "hunger priority");
        check(policy.choose(observation(0, 0, 0, haul, blocked)).actionId().equals("haul"),
            "blocked action never selected");
        check(policy.choose(observation(0, 0, 0)).actionId().isEmpty(), "empty set yields no-op");
        check(policy.choose(observation(0, 0, 0, haul, new Action("alpha", Kind.HAUL, 0, true)))
            .actionId().equals("alpha"), "stable tie breaker");
        boolean duplicateRejected = false;
        try { observation(0, 0, 0, haul, haul); }
        catch (IllegalArgumentException expected) { duplicateRejected = true; }
        check(duplicateRejected, "duplicate IDs rejected");
        System.out.println("PolicyKernelTest: 10 checks passed");
    }
}
