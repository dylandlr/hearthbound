package dev.hearthbound.evidence;

import java.nio.file.Files;
import java.util.List;
import java.util.UUID;

/** Real journal/ledger integration with synthetic receipts, not a Minecraft test. */
public final class VerifiedMillLearningTest {
    private static final UUID WORLD = UUID.randomUUID();
    private static final String CITIZEN = UUID.randomUUID().toString();
    private static int checks;

    private static VerifiedMillLearning.Input input(long assigned, long start, long finish) {
        UUID job = UUID.randomUUID();
        var claim = VerifiedMillAttribution.validate(new VerifiedMillAttribution.Proof(
                WORLD, job, UUID.fromString(CITIZEN), "minecraft:overworld", 17,
                start, finish, 1, 0, 0, 1, true, false));
        var observation = new CausalEvidenceJournal.Observation(WORLD, claim.eventId(),
                "hearthbound:create-process:v1:" + WORLD + ":minecraft:overworld:17:"
                        + job + ":" + start + ":" + finish,
                job.toString(), CITIZEN, "minecraft:overworld", 17, assigned, start, finish);
        return new VerifiedMillLearning.Input(new CausalEvidenceJournal.View(observation,
                CausalEvidenceJournal.State.ADMITTED, true, ""), claim);
    }

    private static VerifiedMillLearning.Replay replay(VerifiedMillLearning.Input... input) {
        return VerifiedMillLearning.replay(WORLD, CITIZEN, List.of(input));
    }
    private static void check(boolean value) {
        checks++;
        if (!value) throw new AssertionError("check " + checks);
    }
    private static void rejects(Runnable call) {
        checks++;
        try { call.run(); } catch (IllegalArgumentException expected) { return; }
        throw new AssertionError("accepted invalid evidence at check " + checks);
    }

    public static void main(String[] args) throws Exception {
        var first = input(10, 20, 30);
        var result = replay(first);
        var step = result.steps().get(0);
        check(step.durationTicks() == 20);
        check(step.personalMilli() == 500);
        check(step.before() == 0);
        check(Math.abs(step.target() - .5 * Math.pow(.999, 20)) < 1e-15);
        check(Math.abs(step.after() - .25 * step.target()) < 1e-15);
        check(Math.abs(step.target() - step.after()) < Math.abs(step.target() - step.before()));
        check(result.equals(replay(first, first)));
        check(result.equals(replay(first))); // queries do not accumulate optimizer updates
        check(replay().value() == 0 && replay().steps().isEmpty());
        var later = input(31, 40, 60);
        var pair = replay(first, later);
        check(pair.equals(replay(later, first)));
        check(pair.steps().size() == 2);
        check(pair.steps().get(1).before() == step.after());
        check(replay(input(0, 20, 30)).value() < result.value()); // actual assignment duration
        rejects(() -> VerifiedMillLearning.replay(UUID.randomUUID(), CITIZEN, List.of(first)));
        rejects(() -> VerifiedMillLearning.replay(WORLD, UUID.randomUUID().toString(), List.of(first)));
        rejects(() -> VerifiedMillLearning.replay(WORLD, CITIZEN,
                java.util.Collections.nCopies(129, first)));
        for (var state : CausalEvidenceJournal.State.values()) {
            if (state == CausalEvidenceJournal.State.ADMITTED) continue;
            rejects(() -> replay(new VerifiedMillLearning.Input(new CausalEvidenceJournal.View(
                    first.view().observation(), state, true, ""), first.claim())));
        }
        rejects(() -> replay(new VerifiedMillLearning.Input(new CausalEvidenceJournal.View(
                first.view().observation(), CausalEvidenceJournal.State.ADMITTED, false, ""), first.claim())));
        var c = first.claim();
        // Individually exercise every identity/chronology part of the join.
        var mismatches = List.of(
                new VerifiedMillAttribution.Claim("other", c.citizenId(), c.jobId(), c.dimension(), c.machine(), 20, 30),
                new VerifiedMillAttribution.Claim(c.eventId(), "other", c.jobId(), c.dimension(), c.machine(), 20, 30),
                new VerifiedMillAttribution.Claim(c.eventId(), c.citizenId(), "other", c.dimension(), c.machine(), 20, 30),
                new VerifiedMillAttribution.Claim(c.eventId(), c.citizenId(), c.jobId(), "other", c.machine(), 20, 30),
                new VerifiedMillAttribution.Claim(c.eventId(), c.citizenId(), c.jobId(), c.dimension(), "18", 20, 30),
                new VerifiedMillAttribution.Claim(c.eventId(), c.citizenId(), c.jobId(), c.dimension(), c.machine(), 21, 30),
                new VerifiedMillAttribution.Claim(c.eventId(), c.citizenId(), c.jobId(), c.dimension(), c.machine(), 20, 31));
        for (var mismatch : mismatches)
            rejects(() -> replay(new VerifiedMillLearning.Input(first.view(), mismatch)));
        var o = first.view().observation();
        var changed = new CausalEvidenceJournal.Observation(WORLD, o.eventId(), o.physicalEvidenceId(),
                o.jobId(), CITIZEN, o.dimension(), o.machinePos(), 11, o.startTick(), o.finishTick());
        rejects(() -> replay(first, new VerifiedMillLearning.Input(new CausalEvidenceJournal.View(
                changed, CausalEvidenceJournal.State.ADMITTED, true, ""), c)));

        var dir = Files.createTempDirectory("verified-mill-learning-");
        var path = dir.resolve("causal.bin");
        try {
            try (var journal = new CausalEvidenceJournal(path, WORLD)) {
                journal.observe(o);
                rejects(() -> replay(new VerifiedMillLearning.Input(journal.inspect(o.eventId()), c)));
                var admitted = journal.reconcile(o.eventId(), expected -> expected.equals(o));
                check(result.equals(replay(new VerifiedMillLearning.Input(admitted, c))));
            }
            try (var journal = new CausalEvidenceJournal(path, WORLD)) {
                rejects(() -> replay(new VerifiedMillLearning.Input(journal.inspect(o.eventId()), c)));
                check(result.equals(replay(new VerifiedMillLearning.Input(
                        journal.reconcile(o.eventId(), expected -> expected.equals(o)), c))));
                var revoked = journal.reconcile(o.eventId(), expected -> false);
                rejects(() -> replay(new VerifiedMillLearning.Input(revoked, c)));
                var stillRevoked = journal.reconcile(o.eventId(), expected -> true);
                rejects(() -> replay(new VerifiedMillLearning.Input(stillRevoked, c)));
            }
            try (var journal = new CausalEvidenceJournal(path, WORLD)) {
                rejects(() -> replay(new VerifiedMillLearning.Input(journal.inspect(o.eventId()), c)));
            }
        } finally {
            Files.deleteIfExists(path);
            Files.deleteIfExists(dir);
        }
        System.out.println("VerifiedMillLearningTest: " + checks + " checks passed (synthetic receipts)");
    }
}
