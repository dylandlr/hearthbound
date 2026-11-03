package dev.hearthbound.evidence;

/** Java 17 deterministic reference contract; tests are not ML evaluation. */
public final class SourceAwareMillPlannerTest {
    private static int checks;
    private static void check(boolean valid) {
        checks++;
        if (!valid) throw new AssertionError("Source planner check "+checks);
    }
    public static void main(String[] args) {
        for (boolean powered:new boolean[]{false,true})
        for (boolean wheat:new boolean[]{false,true})
        for (boolean flour:new boolean[]{false,true})
        for (boolean blocked:new boolean[]{false,true})
        for (boolean busy:new boolean[]{false,true})
        for (SourceAwareMillPlanner.Availability state:SourceAwareMillPlanner.Availability.values()) {
            var obs=new SourceAwareMillPlanner.Observation(
                powered,wheat,flour,blocked,state,busy);
            var action=SourceAwareMillPlanner.decide(obs);
            check(action!=null);
            if (!powered) check(action==SourceAwareMillPlanner.Intent.INSPECT_UNPOWERED);
            else if (flour||blocked) check(action==SourceAwareMillPlanner.Intent.COLLECT_OUTPUT);
            else if(wheat||busy) check(action==SourceAwareMillPlanner.Intent.WAIT_FOR_PROCESSING);
            else switch (state) {
                case UNKNOWN -> check(action==SourceAwareMillPlanner.Intent.INSPECT_SOURCE);
                case EMPTY -> check(action==SourceAwareMillPlanner.Intent.WAIT_FOR_SUPPLY);
                case AVAILABLE -> check(action==SourceAwareMillPlanner.Intent.REQUEST_WHEAT_HAUL);
            }
            if (SourceAwareMillPlanner.dispatchCandidate(action))
                check(powered && !wheat && !flour && !blocked && !busy
                    && state==SourceAwareMillPlanner.Availability.AVAILABLE);
        }
        try {
            new SourceAwareMillPlanner.Observation(true,false,false,false,null,false);
            throw new AssertionError("Missing source knowledge accepted");
        } catch(IllegalArgumentException expected) {checks++;}
        System.out.println("PASS "+checks+" partial source-aware planner checks");
    }
}
