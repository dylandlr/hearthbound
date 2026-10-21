package dev.hearthbound.learning;

import java.util.Arrays;
import java.util.UUID;

/**
 * Lossless, versioned envelope for distinct citizen and task observations.
 * Does not silently pad or substitute one domain's features for another.
 */
public final class UnifiedCitizenObservation {
    public static final int VERSION = 1;
    public record Snapshot(int schemaVersion, UUID citizen, long gameTick,
                           int citizenSchema, double[] citizenFeatures,
                           int researchSchema, double[] researchFeatures) {
        public Snapshot {
            if (schemaVersion != VERSION || citizen == null || gameTick < 0
                    || citizenSchema != CitizenLocalStateSensor.VERSION
                    || citizenFeatures == null || citizenFeatures.length != CitizenLocalStateSensor.WIDTH)
                throw new IllegalArgumentException("invalid citizen domain observation");
            if (researchFeatures == null) {
                if (researchSchema != 0) throw new IllegalArgumentException("absent research domain version must be 0");
            } else if (researchSchema != ResearchObservationVector.VERSION
                    || researchFeatures.length != ResearchObservationVector.WIDTH) {
                throw new IllegalArgumentException("incompatible research domain");
            }
            citizenFeatures = checked(citizenFeatures);
            researchFeatures = researchFeatures == null ? null : checked(researchFeatures);
        }
        @Override public double[] citizenFeatures() { return citizenFeatures.clone(); }
        @Override public double[] researchFeatures() {
            return researchFeatures == null ? null : researchFeatures.clone();
        }
        public boolean hasResearchContext() { return researchFeatures != null; }
        /**
         * Shape guaranteed only when research is present; missing context never becomes a zero vector.
         */
        public double[] flatForResearchModel() {
            if (researchFeatures == null) throw new IllegalStateException("research context unavailable");
            double[] all = Arrays.copyOf(citizenFeatures, citizenFeatures.length + researchFeatures.length);
            System.arraycopy(researchFeatures, 0, all, citizenFeatures.length, researchFeatures.length);
            return all;
        }
    }

    private UnifiedCitizenObservation() {}
    public static Snapshot combine(UUID citizen, long tick, CitizenLocalStateSensor.Snapshot state,
                                   ResearchObservationVector research) {
        if (state == null) throw new IllegalArgumentException("missing citizen state");
        return new Snapshot(VERSION,citizen,tick,state.version(),state.features(),
                research == null ? 0 : research.version(),
                research == null ? null : research.values());
    }
    private static double[] checked(double[] features) {
        double[] result = features.clone();
        for (double x : result)
            if (!Double.isFinite(x) || x < 0 || x > 1)
                throw new IllegalArgumentException("feature out of [0,1]");
        return result;
    }
}
