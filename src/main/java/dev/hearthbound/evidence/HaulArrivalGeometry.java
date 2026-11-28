package dev.hearthbound.evidence;

/** The two existing arrival geometries; no action or completion authority. */
public final class HaulArrivalGeometry {
    public static final double MOTOR_REACH_SQ = 6.25;
    public static final double SMOKE_REACH_SQ = 2.6 * 2.6;
    public record Distances(double motor, double smoke) {}
    private HaulArrivalGeometry() {}

    public static Distances measure(double x, double y, double z,
                                    int destinationX, int destinationY, int destinationZ) {
        if (!Double.isFinite(x) || !Double.isFinite(y) || !Double.isFinite(z))
            throw new IllegalArgumentException("Nonfinite arrival position");
        double dx = x - (destinationX + .5);
        double dz = z - (destinationZ + .5);
        double motorDy = y - (destinationY + .5);
        double smokeDy = y - destinationY;
        double motor = dx * dx + motorDy * motorDy + dz * dz;
        double smoke = dx * dx + smokeDy * smokeDy + dz * dz;
        if (!Double.isFinite(motor) || !Double.isFinite(smoke))
            throw new IllegalArgumentException("Arrival distance overflow");
        return new Distances(motor, smoke);
    }
}
