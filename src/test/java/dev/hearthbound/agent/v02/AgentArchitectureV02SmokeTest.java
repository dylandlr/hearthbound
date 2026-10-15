package dev.hearthbound.agent.v02;

import java.util.Arrays;

public final class AgentArchitectureV02SmokeTest {
    private static void verify(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        encodingContract();
        partialObservation();
        deterministicReplay();
        rejectedActionIsAtomic();
        rewardsStaySeparate();
        scriptedBaselineCompletes();
        System.out.println("PASS: v0.2 agent architecture acceptance suite");
    }

    private static void encodingContract() {
        DeterministicMillSimulator sim = new DeterministicMillSimulator(MillState.homestead(4, 3), 7);
        float[] vector = MillObservationEncoder.encode(sim.observe());
        verify(vector.length == MillObservationEncoder.FEATURE_NAMES.size(), "feature order mismatch");
        for (float value : vector)
            verify(Float.isFinite(value) && value >= 0f && value <= 1f, "unbounded feature");
        verify(MillObservation.VERSION.endsWith("v0.2"), "observation version missing");
    }

    private static void partialObservation() {
        DeterministicMillSimulator sim = new DeterministicMillSimulator(
                new MillState(9, 2, 3, 4, 0, 8, HierarchicalTask.WAIT, false, 0), 1);
        MillObservation observation = sim.observe();
        verify(!observation.sourceVisible() && observation.sourceWheat() == 0, "source leaked");
        verify(!observation.millVisible() && observation.millWheat() == 0
                && observation.millFlour() == 0, "mill leaked");
        verify(observation.storeVisible() && observation.storeFlour() == 4, "visible store hidden");
        float[] vector = MillObservationEncoder.encode(observation);
        verify(vector[2] == 0f && vector[3] == 0f && vector[4] == 0f, "hidden vector leaked");
    }

    private static void deterministicReplay() {
        MillState initial = MillState.homestead(5, 4);
        DeterministicMillSimulator a = new DeterministicMillSimulator(initial, 123);
        DeterministicMillSimulator b = new DeterministicMillSimulator(initial, 123);
        AgentPolicyV02 policy = new ScriptedMillPolicyV02();
        for (int i = 0; i < 12; i++) {
            HierarchicalTask action = policy.decide(a.observe());
            verify(action == policy.decide(b.observe()), "policy replay diverged");
            verify(a.step(action).equals(b.step(action)), "transition replay diverged");
        }
    }

    private static void rejectedActionIsAtomic() {
        DeterministicMillSimulator sim = new DeterministicMillSimulator(MillState.homestead(1, 1), 0);
        MillState before = sim.state();
        DeterministicMillSimulator.Transition transition = sim.step(HierarchicalTask.COLLECT_FLOUR);
        verify(!transition.accepted() && sim.state().equals(before), "rejection mutated state");
        verify(transition.reward().personalComponents().containsKey("invalid_action"), "missing rejection reward");
        verify(transition.reward().colonyTotal() == 0.0, "rejection rewarded colony");
    }

    private static void rewardsStaySeparate() {
        DeterministicMillSimulator sim = new DeterministicMillSimulator(MillState.homestead(1, 1), 0);
        sim.step(HierarchicalTask.SUPPLY_MILL);
        sim.step(HierarchicalTask.COLLECT_FLOUR);
        RewardFrame reward = sim.step(HierarchicalTask.RETURN_TO_WAIT).reward();
        verify(reward.personalComponents().containsKey("completed_delivery"), "personal provenance missing");
        verify(reward.colonyComponents().containsKey("flour_delivered")
                && reward.colonyComponents().containsKey("target_reached"), "colony provenance missing");
        verify(reward.personalTotal() != reward.colonyTotal(), "reward channels collapsed");
    }

    private static void scriptedBaselineCompletes() {
        MillState initial = MillState.homestead(12, 8);
        DeterministicMillSimulator sim = new DeterministicMillSimulator(initial, 42);
        AgentPolicyV02 policy = new ScriptedMillPolicyV02();
        int initialUnits = initial.conservedUnits();
        for (int i = 0; i < 100 && !sim.state().targetReached(); i++) {
            DeterministicMillSimulator.Transition transition = sim.step(policy.decide(sim.observe()));
            verify(transition.accepted(), "baseline chose invalid action");
            verify(sim.state().conservedUnits() == initialUnits, "inventory created or destroyed");
        }
        verify(sim.state().targetReached(), "baseline failed target: " + Arrays.toString(
                MillObservationEncoder.encode(sim.observe())));
    }
}
