package dev.hearthbound.agent.v02;

import java.util.List;

public final class TrajectoryDatasetV02SmokeTest {
    private static void verify(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        List<TrajectoryRecorderV02> first = TrajectoryDatasetV02.generate(
                new ScriptedMillPolicyV02(), 3, 8, 5, 900);
        List<TrajectoryRecorderV02> replay = TrajectoryDatasetV02.generate(
                new ScriptedMillPolicyV02(), 3, 8, 5, 900);
        String jsonl = TrajectoryDatasetV02.toJsonLines(first);

        verify(jsonl.equals(TrajectoryDatasetV02.toJsonLines(replay)), "dataset replay diverged");
        verify(jsonl.lines().count() == 45, "expected three actions per delivered flour");
        verify(jsonl.lines().allMatch(line -> line.contains("\"schema\":\""
                + TrajectoryStepV02.VERSION + "\"")), "trajectory schema missing");
        verify(jsonl.contains("\"personal_rewards\":{\"useful_supply\":0.02}"),
                "personal reward provenance missing");
        verify(jsonl.contains("\"colony_rewards\":{\"flour_delivered\":1.0"),
                "colony reward provenance missing");

        for (TrajectoryRecorderV02 episode : first) {
            verify(episode.steps().get(episode.steps().size() - 1).terminal(), "terminal row missing");
            for (TrajectoryStepV02 row : episode.steps()) {
                verify(row.actionMask().contains(row.action()), "baseline emitted masked action");
                verify(row.observation().length == 20, "unstable feature width");
            }
        }
        System.out.println("PASS: deterministic v0.2 JSONL trajectory dataset");
    }
}
