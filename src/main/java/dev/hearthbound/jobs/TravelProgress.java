package dev.hearthbound.jobs;

/** Pure Java travel-progress watchdog, independent of Minecraft and AI models. */
public final class TravelProgress {
    public enum Outcome { MOVING, ARRIVED, STALLED, TIMED_OUT }
    private final long startedTick;
    private long previousTick;
    private double bestDistanceSq;
    private int stagnantSamples;

    public TravelProgress(long startedTick, double startingDistanceSq) {
        if (startedTick < 0 || !Double.isFinite(startingDistanceSq) || startingDistanceSq < 0)
            throw new IllegalArgumentException("Invalid start");
        this.startedTick = startedTick;
        this.previousTick = startedTick;
        this.bestDistanceSq = startingDistanceSq;
    }

    /** Call no more frequently than once per 20 game ticks; arrival distance is 2 blocks. */
    public Outcome sample(long tick, double distanceSq) {
        if (tick < previousTick || !Double.isFinite(distanceSq) || distanceSq < 0)
            throw new IllegalArgumentException("Invalid travel sample");
        previousTick = tick;
        if (distanceSq <= 4.0) return Outcome.ARRIVED;
        if (tick - startedTick >= 1200) return Outcome.TIMED_OUT;
        if (Math.sqrt(bestDistanceSq) - Math.sqrt(distanceSq) >= 0.5) {
            bestDistanceSq = distanceSq;
            stagnantSamples = 0;
        } else if (++stagnantSamples >= 10) {
            return Outcome.STALLED;
        }
        return Outcome.MOVING;
    }
}
