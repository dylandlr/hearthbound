package dev.hearthbound.learning;

import java.util.Arrays;
import java.util.Objects;
import java.util.UUID;

/**
 * Offline learning contract. Never infer successor observations from a receipt.
 * A verified reward is necessary but not sufficient for a full transition.
 */
public final class ResearchExperienceTransition {
    public enum Completion { SUCCESS, FAILURE, INTERRUPTED }
    public record Sample(int schemaVersion, UUID job, UUID citizen,
                         long decisionTick, long observationTick,
                         long outcomeTick, String evidenceId,
                         int action, double[] state, double[] nextState,
                         OutcomeLedger.RewardVector reward, boolean terminal) {
        public Sample {
            if (schemaVersion != 1 || job == null || citizen == null
                    || evidenceId == null || evidenceId.isBlank()
                    || reward == null || decisionTick < 0
                    || observationTick < outcomeTick || outcomeTick < decisionTick
                    || action < 0 || action > 1
                    || state == null || nextState == null
                    || state.length != ResearchObservationVector.WIDTH
                    || nextState.length != ResearchObservationVector.WIDTH)
                throw new IllegalArgumentException("invalid learning transition");
            state = state.clone();
            nextState = nextState.clone();
            for (double[] vector : new double[][]{state,nextState})
                for (double x : vector)
                    if (!Double.isFinite(x) || x < 0 || x > 1)
                        throw new IllegalArgumentException("invalid feature");
        }
        @Override public double[] state() { return state.clone(); }
        @Override public double[] nextState() { return nextState.clone(); }
    }

    private ResearchExperienceTransition() {}

    /** Explicitly observed post-outcome state; null signifies that the sample is incomplete. */
    public static Sample complete(VerifiedTrainingTransitions.Transition reward,
                                  ResearchObservationVector before,
                                  ResearchObservationVector after,
                                  long successorTick, boolean terminal) {
        Objects.requireNonNull(reward, "verified reward");
        Objects.requireNonNull(before, "pre-decision observation");
        Objects.requireNonNull(after, "successor observation");
        if (!"PROPOSE".equals(reward.action()))
            throw new IllegalArgumentException("unsupported action");
        return new Sample(1, reward.job(), reward.citizen(), reward.decisionTick(),
                successorTick, reward.outcomeTick(), reward.evidenceId(), 1,
                before.values(), after.values(), reward.reward(), terminal);
    }
}
