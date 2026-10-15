package dev.hearthbound.agent.v02;

import java.util.ArrayList;
import java.util.List;

public final class TrajectoryDatasetV02 {
    private TrajectoryDatasetV02() {}

    public static List<TrajectoryRecorderV02> generate(
            AgentPolicyV02 policy, int episodes, int wheat, int target, long seedBase) {
        if (policy == null || episodes < 1 || wheat < 0 || target < 1 || target > wheat)
            throw new IllegalArgumentException("Invalid dataset configuration");
        List<TrajectoryRecorderV02> result = new ArrayList<>();
        for (int episode = 0; episode < episodes; episode++) {
            DeterministicMillSimulator simulator = new DeterministicMillSimulator(
                    MillState.homestead(wheat, target), seedBase + episode);
            TrajectoryRecorderV02 recorder = new TrajectoryRecorderV02("mill-" + episode);
            int budget = Math.max(16, wheat * 4);
            while (!simulator.state().targetReached() && recorder.steps().size() < budget)
                recorder.capture(simulator, policy);
            if (!simulator.state().targetReached())
                throw new IllegalStateException("Policy did not complete episode " + episode);
            result.add(recorder);
        }
        return List.copyOf(result);
    }

    public static String toJsonLines(List<TrajectoryRecorderV02> episodes) {
        StringBuilder out = new StringBuilder();
        for (TrajectoryRecorderV02 episode : episodes) out.append(episode.toJsonLines());
        return out.toString();
    }
}
