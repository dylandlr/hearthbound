package dev.hearthbound.research;
public final class PersistentTickCounterTest {
    private static int assertions;
    private static void eq(long actual,long expected) {if(actual!=expected) throw new AssertionError(actual+" != "+expected); assertions++;}
    private static void rejects(Runnable r,Class<? extends Throwable> expected) {
        try {r.run();throw new AssertionError("Expected "+expected);}catch(Throwable t){if(!expected.isInstance(t))throw t;assertions++;}
    }
    public static void main(String[] args) {
        var a=new PersistentTickCounter(0);
        eq(a.current(),0);eq(a.advance(),1);eq(a.advance(),2);
        var afterRestart=new PersistentTickCounter(a.current());
        eq(afterRestart.current(),2);eq(afterRestart.advance(),3);eq(a.current(),2);
        var large=new PersistentTickCounter(Long.MAX_VALUE-1);eq(large.advance(),Long.MAX_VALUE);
        rejects(large::advance, ArithmeticException.class);
        rejects(()->new PersistentTickCounter(-1), IllegalArgumentException.class);
        System.out.println("PersistentTickCounter: "+assertions+" passed");
    }
}