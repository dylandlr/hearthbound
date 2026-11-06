package dev.hearthbound.evidence;

import java.nio.file.Files;
import java.util.List;
import java.util.UUID;

/** Standalone Java 17 contracts; no actual Minecraft process or reward delivery. */
public final class OutcomeLedgerTest {
    private static int checks;
    private static void yes(boolean value) {
        checks++;
        if (!value) throw new AssertionError("check " + checks);
    }
    private static void rejects(Runnable fn) {
        boolean failed = false;
        try { fn.run(); } catch (IllegalArgumentException | IllegalStateException | ArithmeticException e) { failed = true; }
        yes(failed);
    }
    private static long total(OutcomeLedger.Award award, String recipient, String domain) {
        return award.rewards().stream().filter(r -> r.citizenId().equals(recipient)
                && r.domain().equals(domain)).mapToLong(DurableRewardLedger.Reward::milliPoints).sum();
    }
    public static void main(String[] args) throws Exception {
        UUID world = UUID.randomUUID(), foreignWorld = UUID.randomUUID();
        String job = UUID.randomUUID().toString();
        OutcomeLedger ledger = new OutcomeLedger();
        var farm = new OutcomeLedger.Decision(world,"d-farm","farmer",job,10,"harvest");
        var haul = new OutcomeLedger.Decision(world,"d-haul","hauler",job,20,"haul");
        var research = new OutcomeLedger.Decision(world,"d-research","scientist",job,30,"experiment");
        yes(ledger.register(farm));
        yes(ledger.register(haul));
        yes(ledger.register(research));
        yes(!ledger.register(farm));
        rejects(() -> ledger.register(new OutcomeLedger.Decision(world,"d-farm","other",job,10,"harvest")));
        var shares = List.of(new OutcomeLedger.Contribution("d-research",1,3),
                new OutcomeLedger.Contribution("d-farm",1,0),
                new OutcomeLedger.Contribution("d-haul",2,0));
        var budget = new OutcomeLedger.Budget(801,1100,603);
        var claim = new VerifiedMillAttribution.Claim(
                "hearthbound:mill:v1:"+world+":minecraft:overworld:"+job,
                "hauler",job,"minecraft:overworld","42",40,60);
        var award = ledger.proposeMill(claim,world,"physical-process-01","colony-a",shares,budget);
        yes(ledger.proposalCount()==1);
        yes(total(award,"farmer","personal")==200);
        yes(total(award,"hauler","personal")==401);
        yes(total(award,"scientist","personal")==200);
        yes(total(award,"scientist","research")==603);
        yes(total(award,"colony-a","colony")==1100);
        yes(award.toUncommittedCredit().eventId().equals(claim.eventId()));
        yes(ledger.proposeMill(claim,world,"physical-process-01","colony-a",
                List.of(shares.get(1),shares.get(2),shares.get(0)),budget)==award);
        yes(ledger.proposalCount()==1);
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-b",shares,budget));
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-a",shares,
                new OutcomeLedger.Budget(802,1100,603)));
        rejects(() -> ledger.proposeMill(claim,foreignWorld,"physical-process-01","colony-a",shares,budget));
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-a",
                List.of(shares.get(0),shares.get(0)),budget));
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-a",
                List.of(new OutcomeLedger.Contribution("ghost",1,1),shares.get(1)),budget));
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-a",
                List.of(shares.get(1),shares.get(0)),budget)); // owner hauler missing
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-a",
                List.of(new OutcomeLedger.Contribution("d-haul",0,1)),
                new OutcomeLedger.Budget(1,0,1))); // no personal eligibility
        var future = new OutcomeLedger.Decision(world,"d-future","hauler",job,41,"late");
        ledger.register(future);
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-a",
                List.of(new OutcomeLedger.Contribution("d-future",1,1)),budget));
        String otherJob = UUID.randomUUID().toString();
        ledger.register(new OutcomeLedger.Decision(world,"d-other","hauler",otherJob,20,"haul"));
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-a",
                List.of(new OutcomeLedger.Contribution("d-other",1,1)),budget));
        var colliding = new VerifiedMillAttribution.Claim(
                "hearthbound:mill:v1:"+world+":minecraft:overworld:"+otherJob,
                "hauler",otherJob,"minecraft:overworld","42",40,60);
        rejects(() -> ledger.proposeMill(colliding,world,"physical-process-01","colony-a",
                List.of(new OutcomeLedger.Contribution("d-other",1,1)),budget));
        rejects(() -> ledger.proposeMill(claim,world,"physical-process-01","colony-a",shares,
                new OutcomeLedger.Budget(-1,0,0)));
        rejects(() -> new OutcomeLedger.Contribution("d-haul",-1,0));
        // A reward proposal must never write to the durable ledger on its own.
        var dir = Files.createTempDirectory("hearthbound-causal-proposal");
        try (DurableRewardLedger durable = new DurableRewardLedger(dir.resolve("rewards.bin"))) {
            yes(durable.creditCount()==0);
            yes(ledger.proposalCount()==1);
            // Explicit delivery is restricted to standalone contract tests.
            yes(durable.credit(award.toUncommittedCredit()));
            yes(!durable.credit(award.toUncommittedCredit()));
            yes(durable.total("hauler","personal")==401);
            yes(durable.total("colony-a","colony")==1100);
        }
        try (DurableRewardLedger durable = new DurableRewardLedger(dir.resolve("rewards.bin"))) {
            yes(durable.creditCount()==1);
            yes(durable.total("scientist","research")==603);
        }
        Files.deleteIfExists(dir.resolve("rewards.bin"));
        Files.delete(dir);
        System.out.println("OutcomeLedgerTest: " + checks + " checks passed");
    }
}
