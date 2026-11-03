package dev.hearthbound.perception;

import java.util.List;

public final class SharedPerceptionLedgerTest {
    private static int checks;
    private static void check(boolean ok, String message) {
        checks++;
        if (!ok) throw new AssertionError("check=" + checks + " " + message);
    }
    private static void invalid(Runnable f) {
        try {
            f.run();
            throw new AssertionError("Invalid ledger operation accepted");
        } catch (IllegalArgumentException expected) { checks++; }
    }
    public static void main(String[] args) {
        SharedPerceptionLedger ledger = new SharedPerceptionLedger(4,100);
        ledger.subscribe("farmer", "mill_1");
        ledger.subscribe("hauler", "chest_1");
        ledger.subscribe("researcher", "mill_1");
        var first=ledger.publish("mill_1","power","ON",
                SharedPerceptionLedger.Origin.SERVER_EVENT,"server",5);
        check(first.sequence()==1 && first.observedTick()==100,"monotonic event");
        check(ledger.pending("farmer")==1 && ledger.pending("hauler")==0,
                "scope prevents global broadcast");
        check(ledger.read("farmer","mill_1","power").validity()
                ==SharedPerceptionLedger.Validity.UNKNOWN,"no magic knowledge before delivery");
        check(ledger.drain("farmer").size()==1,"farmer gets subscribed event");
        check(ledger.read("farmer","mill_1","power").fact().value().equals("ON"),
                "delivered observation cached");
        check(ledger.read("hauler","mill_1","power").validity()
                ==SharedPerceptionLedger.Validity.UNKNOWN,"unsubscribed citizen isolated");
        ledger.advance(105);
        check(ledger.read("farmer","mill_1","power").validity()
                ==SharedPerceptionLedger.Validity.CURRENT,"TTL inclusive");
        ledger.advance(106);
        check(ledger.read("farmer","mill_1","power").validity()
                ==SharedPerceptionLedger.Validity.EXPIRED,"TTL expiry");
        check(ledger.read("farmer","mill_1","power").ageTicks()==6,"source age");
        ledger.publish("mill_1","power","OFF",
                SharedPerceptionLedger.Origin.CITIZEN_REPORT,"visitor",2);
        ledger.drain("farmer");
        check(ledger.read("farmer","mill_1","power").fact().value().equals("ON"),
                "citizen hearsay cannot override authoritative fact");
        ledger.publish("mill_1","power","OFF",
                SharedPerceptionLedger.Origin.VISION_PREDICTION,"camera",2);
        ledger.drain("farmer");
        check(ledger.read("farmer","mill_1","power").fact().origin()
                ==SharedPerceptionLedger.Origin.SERVER_EVENT,
                "visual prediction cannot overwrite server evidence");
        ledger.publish("mill_1","power","OFF",
                SharedPerceptionLedger.Origin.DIRECT_OBSERVATION,"farmer",3);
        ledger.drain("farmer");
        check(ledger.read("farmer","mill_1","power").fact().value().equals("OFF"),
                "new direct observation updates source");
        check(ledger.read("farmer","mill_1","power").ageTicks()==0,
                "updated time");
        ledger.unsubscribe("farmer","mill_1");
        check(ledger.read("farmer","mill_1","power").validity()
                ==SharedPerceptionLedger.Validity.UNKNOWN,
                "unsubscribe clears scoped knowledge");
        // With a small mailbox, overflow must be visible. No silent
        // partial cache that pretends complete event delivery.
        SharedPerceptionLedger limited=new SharedPerceptionLedger(2,0);
        limited.subscribe("alpha","chest");
        limited.subscribe("beta","chest");
        for (int j=0;j<5;j++) {
            limited.advance(j);
            limited.publish("chest","wheat",""+j,
                    SharedPerceptionLedger.Origin.SERVER_EVENT,"server",3);
        }
        check(limited.pending("alpha")==2,"bounded inbox");
        check(limited.read("alpha","chest","wheat").validity()
                ==SharedPerceptionLedger.Validity.UNKNOWN,
                "unprocessed events are not cached");
        List<SharedPerceptionLedger.Delivery> seen=limited.drain("alpha");
        check(seen.size()==3 && seen.get(0).gap(),"overflow gap explicitly reported");
        check(limited.read("alpha","chest","wheat").fact().value().equals("4"),
                "latest authoritative update restores knowledge after gap");
        check(limited.pending("beta")==2,"one consumer does not drain another");
        limited.drain("beta");
        check(limited.read("beta","chest","wheat").fact().value().equals("4"),
                "independent subscriber cache");
        invalid(()->new SharedPerceptionLedger(0,0));
        invalid(()->new SharedPerceptionLedger(1,-1));
        invalid(()->ledger.advance(105));
        invalid(()->ledger.subscribe("","chest"));
        invalid(()->ledger.subscribe("citizen",""));
        invalid(()->ledger.publish("chest","stock","AVAILABLE",
                null,"server",4));
        invalid(()->ledger.publish("chest","stock","AVAILABLE",
                SharedPerceptionLedger.Origin.SERVER_EVENT,"server",0));
        check(first.authoritative(),"trusted server origin");
        System.out.println("PASS " + checks + " bounded shared perception, TTL, trust, subscription and gap checks");
    }
}
