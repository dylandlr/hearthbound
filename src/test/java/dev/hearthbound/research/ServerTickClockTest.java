package dev.hearthbound.research;
public final class ServerTickClockTest {
    static int n;
    static void check(boolean v) { if (!v) throw new AssertionError("check "+n); n++; }
    static void reject(Runnable fn) { try { fn.run(); throw new AssertionError("should reject"); } catch (IllegalArgumentException expected) { n++; } }
    public static void main(String[] args) {
        var c = new ServerTickClock(40);
        check(c.current()==40);
        check(c.observe(1000)==40);
        check(c.observe(1000)==40);
        check(c.observe(1001)==41);
        check(c.observe(1005)==45);
        reject(()->c.observe(1004));
        reject(()->c.observe(-1));
        reject(()->new ServerTickClock(-1));
        var restart=new ServerTickClock(c.current());
        check(restart.observe(50)==45);
        check(restart.observe(51)==46);
        check(c.current()==45);
        System.out.println("ServerTickClock: "+n+" checks passed");
    }
}
