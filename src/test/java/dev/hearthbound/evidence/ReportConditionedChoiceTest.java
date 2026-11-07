package dev.hearthbound.evidence;

import java.util.List;
import java.util.UUID;

/** Controlled paired arm test; no Minecraft truth is queried or modified. */
public final class ReportConditionedChoiceTest {
    private static int checks;
    private static void yes(boolean v) {
        checks++;
        if (!v) throw new AssertionError("report-choice assertion " + checks);
    }
    private static void bad(Runnable action) {
        boolean rejected=false;
        try { action.run(); }
        catch (IllegalArgumentException | NullPointerException expected) { rejected=true; }
        yes(rejected);
    }
    private static ReportConditionedChoice.Report report(
            String source, UUID receiver, UUID sender, int wheat, long obs, long deliver) {
        return new ReportConditionedChoice.Report(source, receiver, sender,
            ReportConditionedChoice.ORIGIN, "AVAILABLE", wheat, 1, obs, deliver);
    }
    public static void main(String[] ignored) {
        UUID recipient=UUID.randomUUID(), sender=UUID.randomUUID();
        String a="minecraft:overworld|3,101,1", b="minecraft:overworld|7,101,1";
        long now=120;
        var first=report(a,recipient,sender,3,100,101);
        var second=report(b,recipient,sender,1,100,102);
        var menu=List.of(a,b);
        var exposed=ReportConditionedChoice.choose(recipient,menu,List.of(first,second),
            ReportConditionedChoice.Exposure.EXPOSED,now);
        var withheld=ReportConditionedChoice.choose(recipient,menu,List.of(first,second),
            ReportConditionedChoice.Exposure.WITHHELD,now);
        yes(exposed.status()==ReportConditionedChoice.Status.CHOOSE);
        yes(a.equals(exposed.source()));
        yes(exposed.admissibleReports()==2);
        yes(!exposed.observedWorldInventory());
        yes(withheld.status()==ReportConditionedChoice.Status.ABSTAIN);
        yes(withheld.source()==null);
        yes(withheld.admissibleReports()==0);
        yes(!withheld.observedWorldInventory());
        yes("REPORT_EXPOSURE_WITHHELD".equals(withheld.reason()));
        yes("SCRIPTED_HIGHEST_REPORTED_WHEAT".equals(exposed.reason()));
        // Exposing recipient reports, rather than rewriting source inventory,
        // is the only manipulated decision input in this paired comparison.
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        yes(a.equals(ReportConditionedChoice.choose(recipient,menu,List.of(second,first),
            ReportConditionedChoice.Exposure.EXPOSED,now).source()));
        var richer=report(b,recipient,sender,6,110,111);
        yes(b.equals(ReportConditionedChoice.choose(recipient,menu,List.of(first,richer),
            ReportConditionedChoice.Exposure.EXPOSED,now).source()));
        var tie=report(b,recipient,sender,3,110,111);
        yes(a.equals(ReportConditionedChoice.choose(recipient,menu,List.of(first,tie),
            ReportConditionedChoice.Exposure.EXPOSED,now).source()));
        yes(ReportConditionedChoice.choose(recipient,List.of(a),List.of(second),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        // No secondhand report or owner mismatch is automatically promoted.
        var hearsay=new ReportConditionedChoice.Report(a,recipient,sender,
            "HEARSAY_FROM_THIRD_PERSON", "AVAILABLE",3,1,100,101);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(hearsay),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        var foreign=report(a,UUID.randomUUID(),sender,3,100,101);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(foreign),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        var self=report(a,recipient,recipient,3,100,101);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(self),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        var empty=report(a,recipient,sender,0,100,101);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(empty),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        var future=report(a,recipient,sender,2,125,126);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(future),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        var wrongChronology=report(a,recipient,sender,2,130,100);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(wrongChronology),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        var lateSource=report(a,recipient,sender,2,50,100);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(lateSource),
            ReportConditionedChoice.Exposure.EXPOSED,now).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        var ancient=report(a,recipient,sender,2,50,55);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(ancient),
            ReportConditionedChoice.Exposure.EXPOSED,300).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(first),
            ReportConditionedChoice.Exposure.EXPOSED,301).status()
            ==ReportConditionedChoice.Status.CHOOSE); // 200 ticks inclusive
        yes(ReportConditionedChoice.choose(recipient,menu,List.of(first),
            ReportConditionedChoice.Exposure.EXPOSED,302).status()
            ==ReportConditionedChoice.Status.ABSTAIN);
        bad(() -> ReportConditionedChoice.choose(recipient,List.of(),List.of(first),
            ReportConditionedChoice.Exposure.EXPOSED,now));
        bad(() -> ReportConditionedChoice.choose(recipient,List.of(a,a),List.of(first),
            ReportConditionedChoice.Exposure.EXPOSED,now));
        bad(() -> ReportConditionedChoice.choose(recipient,menu,List.of(first),
            ReportConditionedChoice.Exposure.EXPOSED,-1));
        bad(() -> ReportConditionedChoice.choose(recipient,
            List.of(a,b,"c","d","e","f","g","h","i"),List.of(first),
            ReportConditionedChoice.Exposure.EXPOSED,now));
        bad(() -> new ReportConditionedChoice.Decision(
            ReportConditionedChoice.Status.CHOOSE,null,"invalid",1,
            ReportConditionedChoice.Exposure.EXPOSED,false));
        bad(() -> new ReportConditionedChoice.Decision(
            ReportConditionedChoice.Status.ABSTAIN,a,"invalid",0,
            ReportConditionedChoice.Exposure.EXPOSED,false));
        bad(() -> new ReportConditionedChoice.Decision(
            ReportConditionedChoice.Status.CHOOSE,a,"invalid",1,
            ReportConditionedChoice.Exposure.EXPOSED,true));
        System.out.println("ReportConditionedChoiceTest: " + checks
            + " checks passed (paired visibility controls; no inventory reads, rewards or model updates)");
    }
}
