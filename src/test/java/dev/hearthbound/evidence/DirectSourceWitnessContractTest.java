package dev.hearthbound.evidence;

import java.util.UUID;

/** Explicit unit evidence: a real direct source observer is not an executor. */
public final class DirectSourceWitnessContractTest {
    private static int checks;
    private static void yes(boolean ok) {
        checks++;
        if (!ok) throw new AssertionError("witness check " + checks);
    }
    private static void rejects(Runnable r) {
        boolean denied=false;
        try { r.run(); } catch (IllegalArgumentException | NullPointerException ex) { denied=true; }
        yes(denied);
    }
    public static void main(String[] args) {
        UUID world=UUID.randomUUID(), job=UUID.randomUUID(),
            executor=UUID.randomUUID(), observer=UUID.randomUUID();
        String dimension="minecraft:overworld";
        long source=48672830L, start=100, assigned=110, processing=125;
        var direct=new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,start,2,8,DirectSourceWitnessContract.DIRECT);
        var link=DirectSourceWitnessContract.bind(direct,job,executor,dimension,source,assigned);
        yes(world.equals(link.world()));
        yes(job.equals(link.job()));
        yes(observer.equals(link.observer()));
        yes(!observer.equals(link.executor()));
        yes(link.assignedTick()==110);
        yes(link.sourceRevision()==2);
        yes(link.wheat()==8);
        yes(link.evidenceId().contains(job.toString()));
        yes(link.evidenceId().contains(observer.toString()));
        yes(DirectSourceWitnessContract.matchesProcess(link,direct,world,job,executor,
            dimension,source,assigned,processing));
        yes(!DirectSourceWitnessContract.matchesProcess(link,direct,world,job,executor,
            dimension,source,assigned,assigned)); // no outcome before assignment
        yes(!DirectSourceWitnessContract.matchesProcess(link,direct,UUID.randomUUID(),job,executor,
            dimension,source,assigned,processing));
        yes(!DirectSourceWitnessContract.matchesProcess(link,direct,world,UUID.randomUUID(),executor,
            dimension,source,assigned,processing));
        yes(!DirectSourceWitnessContract.matchesProcess(link,direct,world,job,observer,
            dimension,source,assigned,processing));
        yes(!DirectSourceWitnessContract.matchesProcess(link,direct,world,job,executor,
            "minecraft:the_nether",source,assigned,processing));
        yes(!DirectSourceWitnessContract.matchesProcess(link,direct,world,job,executor,
            dimension,source+1,assigned,processing));
        yes(!DirectSourceWitnessContract.matchesProcess(link,direct,world,job,executor,
            dimension,source,assigned+1,processing));
        var revisionChanged=new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,start,3,8,DirectSourceWitnessContract.DIRECT);
        yes(!DirectSourceWitnessContract.matchesProcess(link,revisionChanged,world,job,executor,
            dimension,source,assigned,processing));
        var quantityChanged=new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,start,2,7,DirectSourceWitnessContract.DIRECT);
        yes(!DirectSourceWitnessContract.matchesProcess(link,quantityChanged,world,job,executor,
            dimension,source,assigned,processing));
        var changedTick=new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,101,2,8,DirectSourceWitnessContract.DIRECT);
        yes(!DirectSourceWitnessContract.matchesProcess(link,changedTick,world,job,executor,
            dimension,source,assigned,processing));
        var foreignWorld=new DirectSourceWitnessContract.DirectSource(UUID.randomUUID(),observer,dimension,
            source,start,2,8,DirectSourceWitnessContract.DIRECT);
        yes(!DirectSourceWitnessContract.matchesProcess(link,foreignWorld,world,job,executor,
            dimension,source,assigned,processing));
        rejects(() -> DirectSourceWitnessContract.bind(direct,job,observer,dimension,source,assigned));
        rejects(() -> DirectSourceWitnessContract.bind(direct,job,executor,dimension,source+1,assigned));
        rejects(() -> DirectSourceWitnessContract.bind(direct,job,executor,dimension,source,99));
        rejects(() -> DirectSourceWitnessContract.bind(direct,job,executor,dimension,source,141));
        var reported=new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,start,2,8,"REPORTED_DIRECT_FORGE_OBSERVATION");
        rejects(() -> DirectSourceWitnessContract.bind(reported,job,executor,dimension,source,assigned));
        rejects(() -> new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,start,0,8,DirectSourceWitnessContract.DIRECT));
        rejects(() -> new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,start,2,0,DirectSourceWitnessContract.DIRECT));
        rejects(() -> new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,-1,2,8,DirectSourceWitnessContract.DIRECT));
        rejects(() -> new DirectSourceWitnessContract.WitnessLink(world,job,executor,observer,
            dimension,source,start,assigned,2,8,DirectSourceWitnessContract.DIRECT,"made-up-id"));
        var oldest=new DirectSourceWitnessContract.DirectSource(world,observer,dimension,
            source,70,1,1,DirectSourceWitnessContract.DIRECT);
        yes(DirectSourceWitnessContract.bind(oldest,job,executor,dimension,source,110)
            .observedTick()==70);
        yes(!DirectSourceWitnessContract.matchesProcess(link,reported,world,job,executor,
            dimension,source,assigned,processing));
        System.out.println("DirectSourceWitnessContractTest: "+checks
            +" passed (operator-assisted witness gate, no credit or autonomous decision)");
    }
}
