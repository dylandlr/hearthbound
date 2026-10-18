package dev.hearthbound.ai;

/** Pure lifecycle gate for the opt-in one-haul then study experiment. */
public final class WorkOfferLifecycle {
    private WorkOfferLifecycle() {}
    /** After a haul is issued, never advance until its exact delivery is proven. */
    public static boolean canAdvance(boolean haulIssued, boolean haulCompleted) {
        return !haulIssued || haulCompleted;
    }
    public static boolean offerHaul(boolean configured, boolean haulIssued, int priority) {
        return configured && !haulIssued && priority > 0;
    }
    public static boolean offerStudy(boolean libraryAvailable, boolean lessonKnown, int priority) {
        return libraryAvailable && !lessonKnown && priority > 0;
    }
}