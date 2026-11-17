package dev.hearthbound.civilization;

import java.util.List;
import java.util.Objects;
import java.util.UUID;

/**
 * Deterministic individual preference model for selecting among already
 * observed, executable tasks. No world reads, task execution or reward grants.
 * Each candidate must have passed the authoritative local Forge sensor.
 */
public final class CitizenGoalPolicy {
    private CitizenGoalPolicy() {}

    /** Traits in [0,100]. Generated deterministically for repeatable trials. */
    public record Traits(int diligence, int exploration, int cooperation) {
        public Traits {
            if (diligence < 0 || diligence > 100 || exploration < 0
                    || exploration > 100 || cooperation < 0 || cooperation > 100)
                throw new IllegalArgumentException("Trait out of range");
        }
    }

    public record Candidate(long taskId, int observedWheat, long distanceSquared,
                            int competingOwners) {
        public Candidate {
            if (taskId <= 0 || observedWheat <= 0 || distanceSquared < 0
                    || competingOwners < 0)
                throw new IllegalArgumentException("Invalid observed candidate");
        }
    }

    public record Selection(long taskId, String goal, long score) {}

    public static Traits fromIdentity(UUID citizen, int seed) {
        Objects.requireNonNull(citizen);
        long n = citizen.getMostSignificantBits() ^ Long.rotateLeft(citizen.getLeastSignificantBits(), 17)
                ^ (0x9e3779b97f4a7c15L * (seed + 1L));
        return new Traits(20 + (int) Math.floorMod(n, 81),
            20 + (int) Math.floorMod(n >>> 21, 81),
            20 + (int) Math.floorMod(n >>> 42, 81));
    }

    /**
     * Chooses only from the supplied observation-gated menu. Ties resolve by
     * task ID so the same seed and observations give repeatable decisions.
     */
    public static Selection select(Traits traits, List<Candidate> candidates) {
        Objects.requireNonNull(traits);
        Objects.requireNonNull(candidates);
        Selection best = null;
        for (Candidate candidate : candidates) {
            Objects.requireNonNull(candidate);
            long score = (long) traits.diligence() * Math.min(candidate.observedWheat(), 64)
                    + (long) traits.exploration() * Math.min(candidate.distanceSquared(), 256) / 16
                    - (long) (101 - traits.cooperation()) * candidate.competingOwners() * 50
                    - candidate.distanceSquared() * 2;
            if (best == null || score > best.score()
                    || (score == best.score() && candidate.taskId() < best.taskId()))
                best = new Selection(candidate.taskId(), "SUPPLY_WHEAT", score);
        }
        return best;
    }
}
