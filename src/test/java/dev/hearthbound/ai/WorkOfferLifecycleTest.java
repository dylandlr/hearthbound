package dev.hearthbound.ai;

public final class WorkOfferLifecycleTest {
    private static void check(boolean actual, boolean expected, String label) {
        if (actual != expected) throw new AssertionError(label);
    }
    public static void main(String[] args) {
        check(WorkOfferLifecycle.offerHaul(true,false,1),true,"fresh haul offered");
        check(WorkOfferLifecycle.offerHaul(true,true,1),false,"issued haul not repeated");
        check(WorkOfferLifecycle.offerHaul(false,false,1),false,"unconfigured haul");
        check(WorkOfferLifecycle.offerHaul(true,false,0),false,"disabled hauling");
        check(WorkOfferLifecycle.offerStudy(true,false,1),true,"unknown lesson");
        check(WorkOfferLifecycle.offerStudy(true,true,1),false,"known lesson not repeated");
        check(WorkOfferLifecycle.offerStudy(false,false,1),false,"missing primer");
        check(WorkOfferLifecycle.offerStudy(true,false,0),false,"disabled study");
        System.out.println("WorkOfferLifecycleTest: 8 checks passed");
    }
}