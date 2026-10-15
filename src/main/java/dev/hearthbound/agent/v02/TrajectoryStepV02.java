package dev.hearthbound.agent.v02;

import java.util.List;
import java.util.Map;

public record TrajectoryStepV02(
        String episodeId,
        int index,
        float[] observation,
        List<HierarchicalTask> actionMask,
        HierarchicalTask action,
        boolean accepted,
        Map<String, Double> personalRewards,
        Map<String, Double> colonyRewards,
        String nextStateFingerprint,
        boolean terminal) {

    public static final String VERSION = "hearthbound.agent.trajectory.v0.2";

    public TrajectoryStepV02 {
        if (episodeId == null || episodeId.isBlank() || index < 0 || observation == null
                || actionMask == null || action == null || personalRewards == null
                || colonyRewards == null || nextStateFingerprint == null)
            throw new IllegalArgumentException("Invalid trajectory step");
        if (observation.length != MillObservationEncoder.FEATURE_NAMES.size())
            throw new IllegalArgumentException("Unexpected observation width");
        observation = observation.clone();
        actionMask = List.copyOf(actionMask);
        personalRewards = Map.copyOf(personalRewards);
        colonyRewards = Map.copyOf(colonyRewards);
    }

    @Override public float[] observation() {
        return observation.clone();
    }
}
