package dev.hearthbound.research;

/** Dependency-free decision cadence checks for citizen study scheduling. */
public final class CitizenDecisionCadenceTest {
    private static void expect(boolean actual, boolean expected, String name) {
        if (actual != expected) throw new AssertionError(name);
    }
    private static CitizenDecisionCadence.Snapshot s(
            CitizenDecisionCadence.WorkState state, boolean enabled, int priority,
            boolean knows, boolean hauling, long tick, long retryAfter) {
        return new CitizenDecisionCadence.Snapshot(
                enabled, priority, knows, hauling, state, tick, retryAfter);
    }
    public static void main(String[] args) {
        var idle=CitizenDecisionCadence.WorkState.IDLE;
        expect(CitizenDecisionCadence.shouldConsider(s(idle,true,1,false,false,500,0)),true,"eligible idle");
        expect(CitizenDecisionCadence.shouldConsider(s(idle,false,1,false,false,500,0)),false,"opt in");
        expect(CitizenDecisionCadence.shouldConsider(s(idle,true,0,false,false,500,0)),false,"priority off");
        expect(CitizenDecisionCadence.shouldConsider(s(idle,true,1,true,false,500,0)),false,"already learned");
        expect(CitizenDecisionCadence.shouldConsider(s(idle,true,1,false,true,500,0)),false,"haul conflict");
        expect(CitizenDecisionCadence.shouldConsider(s(idle,true,1,false,false,499,500)),false,"cooldown");
        expect(CitizenDecisionCadence.shouldConsider(s(CitizenDecisionCadence.WorkState.TRAVELING,true,1,false,false,500,0)),false,"travel commitment");
        expect(CitizenDecisionCadence.shouldConsider(s(CitizenDecisionCadence.WorkState.STUDYING,true,1,false,false,500,0)),false,"study commitment");
        expect(CitizenDecisionCadence.shouldConsider(s(CitizenDecisionCadence.WorkState.COMPLETED,true,1,false,false,500,0)),true,"completed can reconsider unknown lesson");
        expect(CitizenDecisionCadence.shouldConsider(s(CitizenDecisionCadence.WorkState.INTERRUPTED,true,1,false,false,500,0)),true,"interrupted can retry");
        System.out.println("CitizenDecisionCadenceTest: 10 checks passed");
    }
}
