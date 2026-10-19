package dev.hearthbound.research;

import java.util.Comparator;
import java.util.List;

/**
 * Pure Java / LLM-free baseline for selecting physical experiment hypotheses.
 * Candidates must be supplied by a bounded, citizen-local sensor, not an omniscient
 * recipe lookup. This policy never performs the experiment or awards knowledge.
 */
public final class ExperimentSelectionPolicy {
    public static final int VERSION = 1;
    public record Candidate(String recipeId, String inputItem, String machine,
                            String predictedOutput, double novelty, double materialCost,
                            boolean materialVisible, boolean machineVisible,
                            boolean previouslyFalsified) {
        public Candidate {
            if (recipeId == null || recipeId.isBlank() || inputItem == null || inputItem.isBlank()
                    || machine == null || machine.isBlank()
                    || predictedOutput == null || predictedOutput.isBlank())
                throw new IllegalArgumentException("Incomplete experiment candidate");
            for (double n : new double[]{novelty,materialCost})
                if (!Double.isFinite(n) || n < 0 || n > 1)
                    throw new IllegalArgumentException("Candidate scalars must be in [0,1]");
        }
    }
    public record Observation(int version, double curiosity, double scarcity,
                              double fatigue, List<Candidate> localCandidates) {
        public Observation {
            if (version != VERSION || localCandidates == null)
                throw new IllegalArgumentException("Invalid observation schema");
            for (double n : new double[]{curiosity,scarcity,fatigue})
                if (!Double.isFinite(n) || n < 0 || n > 1)
                    throw new IllegalArgumentException("Observation scalars must be in [0,1]");
            localCandidates = List.copyOf(localCandidates);
        }
    }
    public enum Action { PROPOSE, DEFER }
    public record Choice(Action action, Candidate candidate, double utility) {}

    public Choice select(Observation o) {
        if (o == null) throw new IllegalArgumentException("Observation missing");
        if (o.fatigue() >= .85) return new Choice(Action.DEFER,null,0);
        return o.localCandidates().stream()
                .filter(c -> c.materialVisible() && c.machineVisible() && !c.previouslyFalsified())
                .map(c -> new Choice(Action.PROPOSE,c,
                        .50*o.curiosity()+.35*c.novelty()
                        -.35*c.materialCost()*(.5+.5*o.scarcity())-.20*o.fatigue()))
                .filter(c -> c.utility() >= .20)
                .sorted(Comparator.comparingDouble(Choice::utility).reversed()
                        .thenComparing(c -> c.candidate().recipeId()))
                .findFirst().orElse(new Choice(Action.DEFER,null,0));
    }
}
