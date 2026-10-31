package dev.hearthbound.research;

import java.util.Objects;
import java.util.UUID;

/**
 * The narrow trust boundary between real milling evidence and a citizen's
 * research experience. This gate does not itself persist or award credit.
 */
public final class CitizenDiscoveryGate {
    public record Assignment(UUID operationId, UUID citizenId, String worldId,
                             String dimension, String machinePosition,
                             String recipeId, boolean serverAuthorized) {
        public Assignment {
            Objects.requireNonNull(operationId);
            Objects.requireNonNull(citizenId);
        }
    }

    public record Observation(UUID operationId, String worldId, String dimension,
                              String machinePosition, String candidateRecipeId,
                              String executedRecipeId, int consumed,
                              boolean positiveOutputDelta, boolean serverSide) {}

    public record Eligible(UUID operationId, UUID citizenId, String discoveredRecipeId) {}

    public static Eligible validate(Assignment assignment, Observation observation) {
        if (assignment == null || observation == null)
            throw new IllegalArgumentException("Missing citizen assignment or observation");
        if (!assignment.serverAuthorized() || !observation.serverSide())
            throw new IllegalArgumentException("Evidence is not server-authoritative");
        if (!assignment.operationId().equals(observation.operationId()) ||
            !nonBlankMatch(assignment.worldId(), observation.worldId()) ||
            !nonBlankMatch(assignment.dimension(), observation.dimension()) ||
            !nonBlankMatch(assignment.machinePosition(), observation.machinePosition()) ||
            !nonBlankMatch(assignment.recipeId(), observation.executedRecipeId()) ||
            !nonBlankMatch(observation.candidateRecipeId(), observation.executedRecipeId()))
            throw new IllegalArgumentException("Citizen assignment and Create operation disagree");
        if (observation.consumed() != 1 || !observation.positiveOutputDelta())
            throw new IllegalArgumentException("Missing consumed input or output delta");
        return new Eligible(assignment.operationId(), assignment.citizenId(), assignment.recipeId());
    }
    private static boolean nonBlankMatch(String a, String b) {
        return a != null && !a.isBlank() && a.equals(b);
    }
    private CitizenDiscoveryGate() {}
}
