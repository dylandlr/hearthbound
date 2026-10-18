package dev.hearthbound.ai;

/** Pure lifecycle gate for the opt-in one-haul then study experiment. */
public final class WorkOfferLifecycle {
    private WorkOfferLifecycle() {}
    public static boolean offerHaul(boolean configured, boolean haulIssued, int priority) {
        return configured && !haulIssued && priority > 0;
    }
    public static boolean offerStudy(boolean libraryAvailable, boolean lessonKnown, int priority) {
        return libraryAvailable && !lessonKnown && priority > 0;
    }
}