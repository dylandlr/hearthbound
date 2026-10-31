package dev.hearthbound.research;

import java.util.UUID;

public final class CitizenDiscoveryGateTest {
    private static int passed;
    private static final UUID OP = UUID.randomUUID();
    private static final UUID CITIZEN = UUID.randomUUID();
    private static final String WORLD = "world";
    private static final String DIM = "minecraft:overworld";
    private static final String POS = "1,-59,1";
    private static final String RECIPE = "create:milling/wheat";

    private static CitizenDiscoveryGate.Assignment assignment(boolean authorized) {
        return new CitizenDiscoveryGate.Assignment(OP, CITIZEN, WORLD, DIM, POS, RECIPE, authorized);
    }
    private static CitizenDiscoveryGate.Observation observation(boolean output) {
        return new CitizenDiscoveryGate.Observation(OP, WORLD, DIM, POS, RECIPE, RECIPE, 1, output, true);
    }
    private static void reject(CitizenDiscoveryGate.Assignment a, CitizenDiscoveryGate.Observation o) {
        try {
            CitizenDiscoveryGate.validate(a, o);
            throw new AssertionError("Expected rejection");
        } catch (IllegalArgumentException expected) { passed++; }
    }
    public static void main(String[] args) {
        var eligible = CitizenDiscoveryGate.validate(assignment(true), observation(true));
        if (!eligible.citizenId().equals(CITIZEN) || !eligible.operationId().equals(OP)
                || !eligible.discoveredRecipeId().equals(RECIPE)) throw new AssertionError("Wrong citizen");
        passed++;
        reject(null, observation(true));
        reject(assignment(true), null);
        reject(assignment(false), observation(true));
        reject(assignment(true), observation(false));
        reject(assignment(true), new CitizenDiscoveryGate.Observation(OP, WORLD, DIM, POS, RECIPE, RECIPE, 1, true, false));
        reject(assignment(true), new CitizenDiscoveryGate.Observation(OP, WORLD, DIM, POS, RECIPE, RECIPE, 0, true, true));
        reject(assignment(true), new CitizenDiscoveryGate.Observation(UUID.randomUUID(), WORLD, DIM, POS, RECIPE, RECIPE, 1, true, true));
        reject(assignment(true), new CitizenDiscoveryGate.Observation(OP, "wrong-world", DIM, POS, RECIPE, RECIPE, 1, true, true));
        reject(assignment(true), new CitizenDiscoveryGate.Observation(OP, WORLD, "minecraft:nether", POS, RECIPE, RECIPE, 1, true, true));
        reject(assignment(true), new CitizenDiscoveryGate.Observation(OP, WORLD, DIM, "9,9,9", RECIPE, RECIPE, 1, true, true));
        reject(assignment(true), new CitizenDiscoveryGate.Observation(OP, WORLD, DIM, POS, "create:milling/stone", RECIPE, 1, true, true));
        reject(assignment(true), new CitizenDiscoveryGate.Observation(OP, WORLD, DIM, POS, RECIPE, "create:milling/stone", 1, true, true));
        System.out.println("CitizenDiscoveryGate: " + passed + " checks passed");
    }
}
