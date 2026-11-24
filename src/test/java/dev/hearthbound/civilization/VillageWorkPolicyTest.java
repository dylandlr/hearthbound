package dev.hearthbound.civilization;

import java.util.Arrays;
import java.util.List;
import java.util.UUID;
import dev.hearthbound.civilization.VillageWorkPolicy.*;

/** Constructed numerical contracts, not physical Minecraft evidence. */
public final class VillageWorkPolicyTest {
    static final UUID OWNER=new UUID(0,1), OTHER=new UUID(0,2);
    static void check(boolean value){if(!value)throw new AssertionError();}
    static void close(double a,double b){if(Math.abs(a-b)>1e-10)throw new AssertionError(a+" != "+b);}
    static void reject(Runnable run){try{run.run();}catch(IllegalArgumentException|IllegalStateException expected){return;}throw new AssertionError("Invalid input accepted");}
    static Offer offer(String id,Kind kind){return new Offer(id,OWNER,kind,16,1,0,.5,"private-fact",0,0);}
    static Outcome outcome(UUID job,Offer o,long finish,double cost,boolean completed){return new Outcome(job,OWNER,o.kind(),Arrays.stream(o.features()).boxed().toList(),0,finish,cost,completed,completed?"physical:"+job:"");}
    public static void main(String[] args){
        var model=new VillageWorkPolicy(OWNER);Offer bake=offer("bake",Kind.BAKE_BREAD),observe=offer("observe",Kind.OBSERVE);
        check(model.choose(List.of(observe,bake),true).equals(bake));var before=model.score(bake,true);var authored=model.score(bake,false);
        Outcome slow=outcome(new UUID(0,10),bake,1200,3,true);check(model.learn(slow));
        double xx=Arrays.stream(bake.features()).map(x->x*x).sum();
        var after=model.score(bake,true);close(after.predictedTicks(),before.predictedTicks()+xx/(1+xx)*(1200-before.predictedTicks()));
        close(after.predictedCost(),before.predictedCost()+xx/(1+xx)*(3-before.predictedCost()));
        close(after.success(),1);check(after.total()<before.total());check(model.score(bake,false).total()==authored.total());
        check(!model.learn(slow));check(model.snapshot().size()==1);
        reject(()->model.learn(outcome(slow.job(),bake,1201,3,true)));
        reject(()->model.learn(outcome(new UUID(0,11),bake,1199,3,true)));
        for(int i=0;i<8;i++)model.learn(outcome(new UUID(0,20+i),bake,2000+i,5,false));
        check(model.choose(List.of(observe,bake),true).equals(observe));
        check(model.choose(List.of(observe,bake),false).equals(bake));
        var restored=VillageWorkPolicy.restore(OWNER,model.snapshot());check(restored.snapshot().equals(model.snapshot()));check(restored.score(bake,true).equals(model.score(bake,true)));
        check(new VillageWorkPolicy(OTHER).snapshot().isEmpty());
        reject(()->new VillageWorkPolicy(OTHER).score(bake,true));reject(()->new VillageWorkPolicy(OTHER).learn(slow));reject(()->VillageWorkPolicy.restore(OTHER,model.snapshot()));
        reject(()->model.choose(List.of(bake,bake),true));reject(()->model.choose(List.of(),true));
        reject(()->new Offer("bad",OWNER,Kind.BAKE_BREAD,Double.NaN,1,0,0,"",0,0));
        reject(()->new Outcome(new UUID(0,90),OWNER,Kind.BAKE_BREAD,List.of(1.,0.,1.,.5),0,20,0,true,""));
        reject(()->new Outcome(new UUID(0,91),OWNER,Kind.WAIT,List.of(1.,Double.NaN,1.,.5),0,20,0,true,""));
        var tied=new VillageWorkPolicy(OWNER);check(tied.choose(List.of(offer("b",Kind.OBSERVE),offer("a",Kind.OBSERVE)),true).id().equals("a"));
        for(double distance:List.of(0.,16.,64.,128.,4096.))for(Kind kind:Kind.values()){
            var far=new Offer("far",OWNER,kind,distance,1,0,.5,"private-fact",0,0);
            close(tied.score(far,true).total(),tied.score(far,false).total());
        }
        System.out.println("PASS VillageWorkPolicy: numerical RLS, changed ranking, fixed control, ownership, idempotency, corruption rejection, exact replay");
    }
}
