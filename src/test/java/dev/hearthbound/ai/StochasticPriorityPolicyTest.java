package dev.hearthbound.ai;

import java.util.List;
import java.util.Map;
import static dev.hearthbound.ai.ColonyPolicy.*;

/** Dependency-free tests runnable by javac as well as CI. */
public final class StochasticPriorityPolicyTest {
    private static void check(boolean ok,String message) {
        if (!ok) throw new AssertionError(message);
    }
    private static Observation o(int danger,int hunger,int fatigue,Action... actions) {
        return new Observation(21,"sable",hunger,danger,fatigue,List.of(actions));
    }
    public static void main(String[] args) {
        Action flee=new Action("flee",Kind.FLEE,0,true);
        Action eat=new Action("eat",Kind.EAT,0,true);
        Action rest=new Action("rest",Kind.REST,0,true);
        Action haul=new Action("haul",Kind.HAUL,0,true);
        Action operate=new Action("operate",Kind.OPERATE,0,true);
        Action study=new Action("study",Kind.STUDY,0,true);
        var profile = new StochasticPriorityPolicy.Profile(Map.of(
                Kind.HAUL,1,Kind.OPERATE,4),.7,.6,.5);
        var left=new StochasticPriorityPolicy(profile,12L,.7);
        var right=new StochasticPriorityPolicy(profile,12L,.7);
        var ordinary=o(0,0,0,haul,operate);
        for (int i=0;i<100;i++) {
            var a=left.choose(ordinary); var b=right.choose(ordinary);
            check(a.equals(b),"seeded replay");
            check(ActionGate.allowed(ordinary,a),"action gate");
        }
        check(left.choose(o(90,90,90,flee,eat,rest,haul)).actionId().equals("flee"),
                "danger priority");
        check(left.choose(o(0,90,90,eat,rest,haul)).actionId().equals("eat"),
                "hunger priority");
        check(left.choose(o(0,0,90,rest,haul)).actionId().equals("rest"),
                "fatigue priority");
        var disabled = new StochasticPriorityPolicy(
                new StochasticPriorityPolicy.Profile(Map.of(Kind.HAUL,0),0,0,0),1,1);
        check(disabled.choose(o(0,0,0,haul)).actionId().isBlank(),"disabled job");
        check(disabled.choose(o(0,0,0,haul,flee)).actionId().isBlank(),"no random fleeing");
        check(disabled.choose(o(90,0,0,flee,haul)).actionId().equals("flee"),
                "safety ignores work off");
        check(new StochasticPriorityPolicy(profile,2,0)
                .choose(ordinary).actionId().equals("haul"),"deterministic priority");
        var reader=new StochasticPriorityPolicy(
                new StochasticPriorityPolicy.Profile(Map.of(Kind.STUDY,1,Kind.HAUL,4),1,0,0),1,0);
        check(reader.choose(o(0,0,0,study,haul)).actionId().equals("study"),
                "study participates in common action interface");
        System.out.println("StochasticPriorityPolicyTest: 8 checks and seeded replay passed");
    }
}
