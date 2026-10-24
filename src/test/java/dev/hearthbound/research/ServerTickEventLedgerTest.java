package dev.hearthbound.research;
import java.util.*;
public class ServerTickEventLedgerTest {
  static int n;
  static void ok(boolean b){if(!b)throw new AssertionError();n++;}
  static void reject(Runnable action){try {action.run();throw new AssertionError("Expected rejection");}catch(IllegalArgumentException|IllegalStateException expected){n++;}}
  static ServerTickEventLedger.Event add(ServerTickEventLedger l,long t,UUID u,String k){return l.record(t,u,k,"world","minecraft:overworld","0,64,0","create:milling/wheat");}
  public static void main(String[] args){
    UUID a=UUID.randomUUID(),b=UUID.randomUUID(); ServerTickEventLedger l=new ServerTickEventLedger();
    var first=add(l,100,a,"START");ok(first.ordinal()==0);
    var second=add(l,100,b,"START");ok(second.ordinal()==1);
    var third=add(l,101,a,"COMPLETE");ok(third.ordinal()==0);
    ok(l.snapshot().size()==3);
    reject(()->add(l,99,b,"COMPLETE"));
    reject(()->add(l,101,a,"COMPLETE"));
    reject(()->add(l,-1,b,"COMPLETE"));
    var restored=new ServerTickEventLedger();restored.restore(l.snapshot());
    ok(add(restored,101,b,"COMPLETE").ordinal()==1);
    reject(()->add(restored,101,a,"START"));
    reject(()->restored.restore(List.of()));
    reject(()->new ServerTickEventLedger().restore(List.of(third, first)));
    reject(()->new ServerTickEventLedger().restore(List.of(first, first)));
    ok(restored.snapshot().size()==4);
    System.out.println("ServerTickEventLedger: "+n+" checks passed");
  }
}
