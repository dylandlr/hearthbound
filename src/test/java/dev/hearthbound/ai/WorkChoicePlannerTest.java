package dev.hearthbound.ai;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import static dev.hearthbound.ai.ColonyPolicy.*;

public final class WorkChoicePlannerTest {
    private static void check(boolean condition, String why) {
        if (!condition) throw new AssertionError(why);
    }
    public static void main(String[] args) {
        UUID citizen = UUID.randomUUID();
        var offers = List.of(
                new WorkChoicePlanner.Offer("haul:wheat", Kind.HAUL, 40, true),
                new WorkChoicePlanner.Offer("study:primer", Kind.STUDY, 40, true));
        var snapshot = WorkChoicePlanner.observation(citizen, 150,0,0,0,offers);
        var studyFirst = new StochasticPriorityPolicy(new StochasticPriorityPolicy.Profile(
                Map.of(Kind.HAUL,4, Kind.STUDY,1),.5,.5,0),17,0);
        var haulFirst = new StochasticPriorityPolicy(new StochasticPriorityPolicy.Profile(
                Map.of(Kind.HAUL,1, Kind.STUDY,4),.5,.5,0),17,0);
        check(WorkChoicePlanner.choose(snapshot,studyFirst).actionId().equals("study:primer"),
                "study priority wins");
        check(WorkChoicePlanner.choose(snapshot,haulFirst).actionId().equals("haul:wheat"),
                "haul priority wins");
        var noStudy = WorkChoicePlanner.observation(citizen,151,0,0,0,List.of(
                new WorkChoicePlanner.Offer("haul:wheat",Kind.HAUL,40,true),
                new WorkChoicePlanner.Offer("study:primer",Kind.STUDY,40,false)));
        check(WorkChoicePlanner.choose(noStudy,studyFirst).actionId().equals("haul:wheat"),
                "unavailable study cannot be selected");
        var disabled = new StochasticPriorityPolicy(new StochasticPriorityPolicy.Profile(
                Map.of(Kind.HAUL,0,Kind.STUDY,0),.5,.5,0),17,0);
        check(WorkChoicePlanner.choose(snapshot,disabled).actionId().isEmpty(),
                "disabled jobs are not selected");
        check(WorkChoicePlanner.choose(snapshot,o ->
                new Decision(149,"haul:wheat","stale")).actionId().isEmpty(),
                "stale proposal rejected");
        System.out.println("WorkChoicePlannerTest: 5 checks passed");
    }
}
