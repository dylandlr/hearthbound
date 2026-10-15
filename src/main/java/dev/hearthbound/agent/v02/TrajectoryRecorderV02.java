package dev.hearthbound.agent.v02;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

public final class TrajectoryRecorderV02 {
    private final String episodeId;
    private final List<TrajectoryStepV02> steps = new ArrayList<>();

    public TrajectoryRecorderV02(String episodeId) {
        if (episodeId == null || episodeId.isBlank()) throw new IllegalArgumentException("episodeId");
        this.episodeId = episodeId;
    }

    public TrajectoryStepV02 capture(DeterministicMillSimulator simulator, AgentPolicyV02 policy) {
        MillObservation observation = simulator.observe();
        HierarchicalTask action = policy.decide(observation);
        DeterministicMillSimulator.Transition transition = simulator.step(action);
        TrajectoryStepV02 row = new TrajectoryStepV02(
                episodeId, steps.size(), MillObservationEncoder.encode(observation),
                observation.actionMask().stream().sorted(Comparator.comparing(Enum::name)).toList(),
                action, transition.accepted(),
                transition.reward().personalComponents(), transition.reward().colonyComponents(),
                fingerprint(transition.after()), transition.after().targetReached());
        steps.add(row);
        return row;
    }

    public List<TrajectoryStepV02> steps() {
        return List.copyOf(steps);
    }

    public String toJsonLines() {
        StringBuilder out = new StringBuilder();
        for (TrajectoryStepV02 row : steps) out.append(json(row)).append('\n');
        return out.toString();
    }

    private static String fingerprint(MillState s) {
        return s.sourceWheat() + ":" + s.millWheat() + ":" + s.millFlour() + ":"
                + s.storeFlour() + ":" + s.cargoFlour() + ":" + s.flourTarget()
                + ":" + s.currentTask().name() + ":" + s.lastActionFailed() + ":" + s.step();
    }

    private static String json(TrajectoryStepV02 r) {
        return "{\"schema\":\"" + TrajectoryStepV02.VERSION
                + "\",\"observation_schema\":\"" + MillObservationEncoder.VERSION
                + "\",\"episode\":\"" + escape(r.episodeId())
                + "\",\"index\":" + r.index()
                + ",\"observation\":" + floats(r.observation())
                + ",\"action_mask\":" + strings(r.actionMask().stream().map(Enum::name).toList())
                + ",\"action\":\"" + r.action().name()
                + "\",\"accepted\":" + r.accepted()
                + ",\"personal_rewards\":" + map(r.personalRewards())
                + ",\"colony_rewards\":" + map(r.colonyRewards())
                + ",\"next_state\":\"" + escape(r.nextStateFingerprint())
                + "\",\"terminal\":" + r.terminal() + "}";
    }

    private static String floats(float[] values) {
        StringBuilder b = new StringBuilder("[");
        for (int i = 0; i < values.length; i++) {
            if (i > 0) b.append(',');
            b.append(Float.toString(values[i]));
        }
        return b.append(']').toString();
    }

    private static String strings(List<String> values) {
        StringBuilder b = new StringBuilder("[");
        for (int i = 0; i < values.size(); i++) {
            if (i > 0) b.append(',');
            b.append('\"').append(escape(values.get(i))).append('\"');
        }
        return b.append(']').toString();
    }

    private static String map(Map<String, Double> values) {
        StringBuilder b = new StringBuilder("{");
        boolean first = true;
        for (var entry : values.entrySet().stream().sorted(Map.Entry.comparingByKey()).toList()) {
            if (!first) b.append(',');
            first = false;
            b.append('\"').append(escape(entry.getKey())).append("\":").append(entry.getValue());
        }
        return b.append('}').toString();
    }

    private static String escape(String value) {
        return value.replace("\\", "\\\\").replace("\"", "\\\"")
                .replace("\n", "\\n").replace("\r", "\\r");
    }
}
