package dev.hearthbound.evidence;

/** Standalone geometry contract; this does not execute Forge or prove arrival. */
public final class HaulArrivalGeometryTest {
    private static void require(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        var insertion = HaulArrivalGeometry.measure(6, 100, 1.5, 7, 100, 1);
        require(insertion.motor() == 2.5 && insertion.smoke() == 2.25, "Independent coordinates");
        require(insertion.motor() <= HaulArrivalGeometry.MOTOR_REACH_SQ
                && insertion.smoke() <= HaulArrivalGeometry.SMOKE_REACH_SQ, "Valid insertion");
        var later = HaulArrivalGeometry.measure(20, 100, 1.5, 7, 100, 1);
        require(later.motor() > HaulArrivalGeometry.MOTOR_REACH_SQ
                && later.smoke() > HaulArrivalGeometry.SMOKE_REACH_SQ, "Later remote pose");
        require(insertion.smoke() == 2.25, "Later observation cannot rewrite insertion");
        var mismatch = HaulArrivalGeometry.measure(7.5, 103, 1.5, 7, 100, 1);
        require(mismatch.motor() == 6.25 && mismatch.smoke() == 9.0,
                "Existing centers are different");
        require(mismatch.smoke() > HaulArrivalGeometry.SMOKE_REACH_SQ,
                "Passing motor radius cannot substitute for smoke radius");
        for (double bad : new double[] {Double.NaN, Double.POSITIVE_INFINITY,
                                       Double.NEGATIVE_INFINITY, Double.MAX_VALUE}) {
            try {
                HaulArrivalGeometry.measure(bad, 100, 1.5, 7, 100, 1);
                throw new AssertionError("Invalid position accepted");
            } catch (IllegalArgumentException expected) { }
        }
        System.out.println("HAUL_ARRIVAL_GEOMETRY_PASS native_runtime_executed=false");
    }
}
