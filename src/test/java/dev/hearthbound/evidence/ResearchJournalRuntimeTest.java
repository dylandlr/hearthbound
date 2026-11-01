package dev.hearthbound.evidence;
import java.nio.file.*;
import java.util.*;
/** Standalone journal replay test: never treated as a Minecraft end-to-end test. */
public final class ResearchJournalRuntimeTest {
 private static int checks;
 private static void check(boolean b){checks++;if(!b)throw new AssertionError("check "+checks);}
 public static void main(String[] args)throws Exception{
  Path dir=Files.createTempDirectory("hb-journal");
  try{
   Path inbox=dir.resolve("inbox.bin"),ledger=dir.resolve("rewards.bin");
   String citizen=UUID.randomUUID().toString();
   String job=UUID.randomUUID().toString();
   VerifiedMillAttribution.Claim claim=new VerifiedMillAttribution.Claim(
      "hearthbound:mill:v1:"+UUID.randomUUID()+":minecraft:overworld:"+job,
      citizen,job,"minecraft:overworld","42",10,20);
   try(ResearchJournalRuntime runtime=new ResearchJournalRuntime(inbox,ledger)){
    check(runtime.enqueue(claim));
    check(!runtime.enqueue(claim));
    check(runtime.pendingCount()==1);
    check(runtime.researchMilliPoints(citizen)==0);
   }
   try(AttributedMillInbox pending=new AttributedMillInbox(inbox);
       DurableRewardLedger credited=new DurableRewardLedger(ledger)){
    check(pending.pendingCount()==1);
    check(credited.credit(new DurableRewardLedger.Credit(claim.eventId(),
       List.of(new DurableRewardLedger.Reward(citizen,"research",1000)))));
    check(credited.total(citizen,"research")==1000);
   }
   try(ResearchJournalRuntime runtime=new ResearchJournalRuntime(inbox,ledger)){
    check(runtime.pendingCount()==1);
    runtime.drainUnsafeForStandaloneTestsOnly();
    check(runtime.pendingCount()==0);
    check(runtime.researchMilliPoints(citizen)==1000);
   }
   try(ResearchJournalRuntime runtime=new ResearchJournalRuntime(inbox,ledger)){
    check(runtime.pendingCount()==0);
    check(runtime.researchMilliPoints(citizen)==1000);
   }
   System.out.println("PASS "+checks+" checks");
  }finally{try(var all=Files.walk(dir)){all.sorted(Comparator.reverseOrder()).forEach(p->{
   try{Files.deleteIfExists(p);}catch(Exception e){throw new RuntimeException(e);}
  });}}
 }
}
