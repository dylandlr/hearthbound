package dev.hearthbound.civilization;

import java.util.List;
import java.util.UUID;
import dev.hearthbound.civilization.CitizenGoalPolicy.*;
import static dev.hearthbound.civilization.CitizenGoalPolicy.fromIdentity;
import static dev.hearthbound.civilization.CitizenGoalPolicy.select;

public final class CitizenGoalPolicyTest {
    private static void check(boolean v) {
        if (!v) throw new AssertionError("Goal selection test failed");
    }
    public static void main(String[] args) {
        UUID id = UUID.fromString("00000000-0000-0000-0000-000000000123");
        check(fromIdentity(id, 42).equals(fromIdentity(id, 42)));
        check(!fromIdentity(id, 42).equals(fromIdentity(id, 43)));
        Traits t = new Traits(90, 25, 60);
        Candidate near = new Candidate(2, 2, 4, 0);
        Candidate rich = new Candidate(1, 12, 100, 0);
        check(select(t, List.of(near, rich)).taskId() == 1);
        check(select(t, List.of()) == null);
        check(select(t, List.of(new Candidate(2, 3, 9, 0),
                new Candidate(1, 3, 9, 0))).taskId() == 1);
        Candidate contested = new Candidate(3, 10, 4, 2);
        check(select(new Traits(20, 20, 10), List.of(near, contested)).taskId() == 2);
        boolean rejected = false;
        try { new Candidate(4, 0, 0, 0); }
        catch (IllegalArgumentException expected) { rejected = true; }
        check(rejected);
        System.out.println("Citizen goal policy: PASS");
    }
}
