package dev.hearthbound.ai;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Random;
import static dev.hearthbound.ai.ColonyPolicy.*;

/**
 * Priority-weighted, reproducibly stochastic implementation of ColonyPolicy.
 * Uses the existing ActionGate contract. Safety-critical actions remain hard
 * overrides; the temperature only affects ordinary eligible work.
 */
public final class StochasticPriorityPolicy implements ColonyPolicy {
    public record Profile(Map<Kind, Integer> priorityByKind, double curiosity,
                          double conscientiousness, double impulsivity) {
        public Profile {
            priorityByKind = Map.copyOf(Objects.requireNonNull(priorityByKind));
            for (double v : new double[]{curiosity, conscientiousness, impulsivity})
                if (!Double.isFinite(v) || v < 0 || v > 1)
                    throw new IllegalArgumentException("Trait outside [0,1]");
            for (var e : priorityByKind.entrySet())
                if (e.getValue() < 0 || e.getValue() > 4)
                    throw new IllegalArgumentException("Priority outside [0,4]");
        }
    }
    private final Profile profile;
    private final Random random;
    private final double baseTemperature;

    public StochasticPriorityPolicy(Profile profile, long seed, double temperature) {
        this.profile = Objects.requireNonNull(profile);
        if (!Double.isFinite(temperature) || temperature < 0)
            throw new IllegalArgumentException("Invalid temperature");
        random = new Random(seed);
        baseTemperature = temperature;
    }

    @Override public Decision choose(Observation o) {
        Objects.requireNonNull(o);
        List<Action> executable = o.availableActions().stream().filter(Action::executable).toList();
        // Safety actions are never disabled by work-priority settings.
        for (Kind emergency : new Kind[]{Kind.FLEE, Kind.EAT, Kind.REST}) {
            boolean triggered = switch (emergency) {
                case FLEE -> o.danger() >= 60;
                case EAT -> o.hunger() >= 70;
                case REST -> o.fatigue() >= 80;
                default -> false;
            };
            if (triggered) {
                var candidate = executable.stream().filter(a -> a.kind() == emergency)
                        .min(Comparator.comparing(Action::id));
                if (candidate.isPresent())
                    return new Decision(o.version(), candidate.get().id(),
                            "Safety override: " + emergency);
            }
        }
        List<Action> candidates = executable.stream()
                .filter(a -> a.kind() != Kind.FLEE && a.kind() != Kind.EAT
                        && a.kind() != Kind.REST)
                .filter(a -> profile.priorityByKind().getOrDefault(a.kind(), 3) > 0).toList();
        if (candidates.isEmpty()) return new Decision(o.version(), "", "No permitted work");
        List<Double> scores = new ArrayList<>();
        double max = Double.NEGATIVE_INFINITY;
        for (Action a : candidates) {
            int p = profile.priorityByKind().getOrDefault(a.kind(), 3);
            double score = 2.0 * (5-p)/4.0 + .3*a.priority()/100.0;
            if (a.kind() == Kind.OPERATE) score += .3*profile.curiosity();
            if (a.kind() == Kind.HAUL || a.kind() == Kind.DELIVER)
                score += .2*profile.conscientiousness();
            scores.add(score);
            max = Math.max(max, score);
        }
        double temperature = baseTemperature * (1 + profile.impulsivity());
        if (temperature == 0) {
            int best=0;
            for (int i=1;i<candidates.size();i++)
                if (scores.get(i)>scores.get(best)
                        || (scores.get(i).equals(scores.get(best))
                        && candidates.get(i).id().compareTo(candidates.get(best).id())<0)) best=i;
            return new Decision(o.version(), candidates.get(best).id(), "Priority baseline");
        }
        double total=0;
        double[] weights=new double[candidates.size()];
        for (int i=0;i<weights.length;i++) {
            weights[i]=Math.exp((scores.get(i)-max)/temperature);
            total+=weights[i];
        }
        double pick=random.nextDouble()*total, cumulative=0;
        for (int i=0;i<weights.length;i++) {
            cumulative+=weights[i];
            if (pick<cumulative || i==weights.length-1)
                return new Decision(o.version(), candidates.get(i).id(),
                        "Stochastic priority selection");
        }
        throw new AssertionError();
    }
}
