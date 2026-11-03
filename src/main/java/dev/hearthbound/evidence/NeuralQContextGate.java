package dev.hearthbound.evidence;

/**
 * Fail-closed action applicability gate for experimental 3-action neural Q.
 * Separate from Forge task authorization. Unsupported contexts abstain.
 * This is an evaluation guard, not permission to execute Minecraft actions.
 */
public final class NeuralQContextGate {
    public enum Decision {
        INSPECT_SOURCE, WAIT_FOR_SUPPLY, REQUEST_WHEAT_HAUL, ABSTAIN
    }
    private NeuralQContextGate() {}

    public static Decision classify(double[] v2, int proposedAction) {
        if(v2 == null || v2.length != 10 || proposedAction < 0 || proposedAction > 2)
            throw new IllegalArgumentException("Invalid v2 neural decision");
        for(double v:v2) if (!Double.isFinite(v) || v < 0 || v > 1)
            throw new IllegalArgumentException("Nonfinite or out-of-range tensor");
        if (v2[5]+v2[6]+v2[7]!=1.0)
            throw new IllegalArgumentException("Invalid source knowledge mask");
        if (v2[9]==1.0 && v2[5]!=1.0)
            throw new IllegalArgumentException("Stale source must be unknown");
        // Neural Q has NO legal action for unpowered, blocked, occupied, or
        // processing/collect-output states. The proposal is always discarded.
        if(v2[0] != 1.0 || v2[1]!=0. || v2[2]!=0. ||
           v2[3]!=0. || v2[8]!=0.)
            return Decision.ABSTAIN;
        if(v2[9]==1.0) return Decision.ABSTAIN;
        // A predicted action for a different source state is also rejected.
        if(proposedAction==0 && v2[5]==1.) return Decision.INSPECT_SOURCE;
        if(proposedAction==1 && v2[6]==1.) return Decision.WAIT_FOR_SUPPLY;
        if(proposedAction==2 && v2[7]==1.) return Decision.REQUEST_WHEAT_HAUL;
        return Decision.ABSTAIN;
    }

    public static boolean canProposeHaul(Decision result) {
        return result==Decision.REQUEST_WHEAT_HAUL;
    }
}
