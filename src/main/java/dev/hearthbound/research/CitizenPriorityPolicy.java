package dev.hearthbound.research;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Random;

/**
 * Deterministic-seed, priority-guided stochastic scheduler policy.
 * Does not perform world actions. Only a scheduler may dispatch its choice.
 */
public final class CitizenPriorityPolicy {
    public enum Job { FARM, BUILD, RESEARCH, STUDY, HAUL, SOCIALIZE, RECREATE, REST }
    /** Priority 1 strongest, 4 weakest, 0 disabled. */
    public record Candidate(Job job, int priority, double need, double traitAffinity,
                            double skill, double colonyDemand, boolean available) {
        public Candidate {
            Objects.requireNonNull(job);
            if (priority < 0 || priority > 4) throw new IllegalArgumentException("priority out of range");
            for (double n : new double[]{need,traitAffinity,skill,colonyDemand})
                if (!Double.isFinite(n) || n < 0 || n > 1)
                    throw new IllegalArgumentException("feature outside [0,1]");
        }
    }
    public record Choice(Job job, double score, double probability) {}

    public static Choice choose(List<Candidate> candidates, double temperature, Random random) {
        Objects.requireNonNull(candidates);
        Objects.requireNonNull(random);
        if (!Double.isFinite(temperature) || temperature < 0)
            throw new IllegalArgumentException("temperature must be finite and nonnegative");
        List<Candidate> legal = candidates.stream()
                .filter(c -> c.available() && c.priority() != 0).toList();
        if (legal.isEmpty()) return null;
        if (legal.stream().map(Candidate::job).distinct().count() != legal.size())
            throw new IllegalArgumentException("duplicate jobs");
        List<Double> scores = legal.stream().map(CitizenPriorityPolicy::score).toList();
        int best = 0;
        for (int i=1;i<scores.size();i++)
            if (scores.get(i)>scores.get(best)) best=i;
        if (temperature==0) return new Choice(legal.get(best).job(), scores.get(best),1);
        double max=scores.stream().max(Comparator.naturalOrder()).orElseThrow();
        double total=0;
        List<Double> weights=new ArrayList<>();
        for (double score:scores) {
            double w=Math.exp((score-max)/temperature);
            weights.add(w);
            total+=w;
        }
        double draw=random.nextDouble()*total;
        double cumulative=0;
        for (int i=0;i<legal.size();i++) {
            cumulative+=weights.get(i);
            if (draw < cumulative || i==legal.size()-1)
                return new Choice(legal.get(i).job(),scores.get(i),weights.get(i)/total);
        }
        throw new AssertionError("unreachable");
    }

    private static double score(Candidate c) {
        // Scores/weights are baselines and require empirical calibration.
        double assigned = (5.0-c.priority())/4.0;
        return 1.8*assigned + 2.0*c.need() + .7*c.traitAffinity()
                + .5*c.skill() + 1.0*c.colonyDemand();
    }
}
