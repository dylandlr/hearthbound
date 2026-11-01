package dev.hearthbound.evidence;
import java.io.IOException;
import java.util.List;
import java.util.Objects;

/** Standalone delivery coordinator; caller-supplied flags are NOT production authorization. */
public final class ResearchReceiptDelivery {
 private ResearchReceiptDelivery(){}
 public static boolean submit(AttributedMillInbox inbox,AttributedMillInbox.Entry entry,
                              boolean verifiedServerReceipt,boolean startupReady)throws IOException{
  Objects.requireNonNull(inbox);Objects.requireNonNull(entry);
  if(!verifiedServerReceipt||!startupReady)throw new IllegalStateException("research export not authorized");
  return inbox.enqueue(entry);
 }
 public static void drain(AttributedMillInbox inbox,DurableRewardLedger ledger,
                          boolean startupReady)throws Exception{
  Objects.requireNonNull(inbox);Objects.requireNonNull(ledger);
  if(!startupReady)throw new IllegalStateException("startup reconciliation incomplete");
  inbox.drain(entry->ledger.credit(new DurableRewardLedger.Credit(entry.eventId(),
      List.of(new DurableRewardLedger.Reward(entry.citizenId(),"research",1000)))));
 }
}
