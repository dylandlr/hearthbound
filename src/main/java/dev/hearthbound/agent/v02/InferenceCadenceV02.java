package dev.hearthbound.agent.v02;

public final class InferenceCadenceV02 {
    public static final int DEFAULT_INTERVAL_TICKS = 20;

    private InferenceCadenceV02() {}

    public static boolean shouldRun(long now, long lastDecision, int intervalTicks,
            boolean activeOperation, boolean terminal) {
        if (now < 0 || lastDecision < -1 || intervalTicks < 1)
            throw new IllegalArgumentException("Invalid inference cadence");
        return !activeOperation && !terminal
                && (lastDecision < 0 || now - lastDecision >= intervalTicks);
    }
}
