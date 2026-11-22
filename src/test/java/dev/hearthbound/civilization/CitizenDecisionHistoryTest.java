package dev.hearthbound.civilization;

import java.util.UUID;
import dev.hearthbound.civilization.CitizenDecisionHistory.*;

public final class CitizenDecisionHistoryTest {
    private static int checks;
    private static final UUID CITIZEN = new UUID(1,1), EPISODE = new UUID(2,2);
    private static final UUID JOB1 = new UUID(3,3), JOB2 = new UUID(3,4);
    private static void yes(boolean ok,String name){checks++;if(!ok)throw new AssertionError(name);}
    private static void rejects(Runnable call,String name){
        checks++;try{call.run();}catch(IllegalArgumentException expected){return;}
        throw new AssertionError(name);
    }
    private static Entry entry(UUID job,long task){
        return new Entry(task,CITIZEN,job,EPISODE,new UUID(4,task),new UUID(5,task),
            1,10,11,12,-1,17,18,Status.ASSIGNED);
    }
    public static void main(String[] args) {
        CitizenDecisionHistory history=new CitizenDecisionHistory(2);
        Entry a=entry(JOB1,1), b=entry(JOB2,2);
        yes(history.register(a),"first recorded");
        yes(history.register(a),"exact registration idempotent");
        yes(history.snapshot().size()==1,"one entry");
        rejects(()->history.register(new Entry(1,CITIZEN,JOB1,EPISODE,a.decision(),a.evidence(),
            2,10,11,12,-1,17,18,Status.ASSIGNED)),"conflicting registration");
        rejects(()->history.register(entry(JOB2,1)),"same task another job");
        yes(!history.complete(JOB2,CITIZEN,EPISODE,15,17,18),"unknown completion excluded");
        rejects(()->history.complete(JOB1,new UUID(9,9),EPISODE,15,17,18),"foreign citizen");
        rejects(()->history.complete(JOB1,CITIZEN,new UUID(9,9),15,17,18),"foreign episode");
        rejects(()->history.complete(JOB1,CITIZEN,EPISODE,11,17,18),"early delivery");
        yes(history.complete(JOB1,CITIZEN,EPISODE,15,17,18),"verified completion");
        yes(history.complete(JOB1,CITIZEN,EPISODE,15,17,18),"exact completion replay");
        rejects(()->history.complete(JOB1,CITIZEN,EPISODE,16,17,18),"conflicting replay");
        yes(history.snapshot().get(0).status()==Status.PHYSICALLY_COMPLETED,"transition stored");
        yes(history.register(b),"second recorded");
        yes(!history.register(entry(new UUID(3,5),3)),"capacity fails closed");
        yes(history.deniedCapacity()==1,"capacity diagnostics");
        CitizenDecisionHistory restored=new CitizenDecisionHistory(2);
        for(Entry e:history.snapshot())restored.restore(e);
        yes(restored.snapshot().equals(history.snapshot()),"exact restore");
        rejects(()->restored.restore(history.snapshot().get(0)),"restore duplicate");
        yes(restored.complete(JOB1,CITIZEN,EPISODE,15,17,18),"replay after restore");
        rejects(()->new Entry(4,CITIZEN,new UUID(4,4),EPISODE,new UUID(5,5),
            new UUID(6,6),1,0,1,25,-1,17,18,Status.ASSIGNED),"expired source");
        rejects(()->new Entry(4,CITIZEN,new UUID(4,4),EPISODE,new UUID(5,5),
            new UUID(6,6),1,0,1,2,9,17,18,Status.ASSIGNED),"unverified delivery");
        rejects(()->new Entry(4,CITIZEN,new UUID(4,4),EPISODE,new UUID(5,5),
            new UUID(6,6),1,0,1,2,1,17,18,Status.PHYSICALLY_COMPLETED),"early completed");
        System.out.println("PASS "+checks+" citizen decision history checks");
    }
}
