package dev.hearthbound.jobs;

public final class TravelProgressSmokeTest {
    static void check(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }
    public static void main(String[] args) {
        TravelProgress arrived = new TravelProgress(0, 100);
        check(arrived.sample(20, 64) == TravelProgress.Outcome.MOVING, "moving");
        check(arrived.sample(40, 1) == TravelProgress.Outcome.ARRIVED, "arrived");
        TravelProgress stalled = new TravelProgress(0, 100);
        for (int i = 1; i < 10; i++) check(stalled.sample(i * 20, 100) == TravelProgress.Outcome.MOVING, "stalled too soon");
        check(stalled.sample(200, 100) == TravelProgress.Outcome.STALLED, "stall not detected");
        TravelProgress timed = new TravelProgress(0, 100);
        check(timed.sample(1200, 100) == TravelProgress.Outcome.TIMED_OUT, "timeout");
        TravelProgress advancing = new TravelProgress(0, 100);
        for (int i=1; i<15; i++) check(advancing.sample(i*20, Math.pow(10 - i*0.6, 2)) != TravelProgress.Outcome.STALLED, "progress not recognized");
        boolean rejected=false;
        try { new TravelProgress(0, -1); } catch (IllegalArgumentException e) { rejected=true; }
        check(rejected, "negative position allowed");
        rejected=false;
        try { arrived.sample(10, 1); } catch (IllegalArgumentException e) { rejected=true; }
        check(rejected, "backward clock allowed");
        System.out.println("PASS: travel progress, arrival, stall, timeout, validation");
    }
}
