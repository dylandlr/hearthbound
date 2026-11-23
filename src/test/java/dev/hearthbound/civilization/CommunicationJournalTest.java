package dev.hearthbound.civilization;

import dev.hearthbound.civilization.CommunicationJournal.Event;
import dev.hearthbound.civilization.CommunicationJournal.Message;
import dev.hearthbound.civilization.CommunicationJournal.Stage;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

public final class CommunicationJournalTest {
    private static int checks;
    private static final UUID WORLD = id(1), EPISODE = id(2);
    private static final UUID SENDER = id(3), RECIPIENT = id(4), OTHER = id(5);
    private static final UUID DECISION = id(20), JOB = id(30);

    private static UUID id(long n) { return new UUID(1, n); }
    private static void yes(boolean ok, String name) {
        checks++;
        if (!ok) throw new AssertionError(name);
    }
    private static void rejects(Runnable call, String name) {
        checks++;
        try { call.run(); } catch (IllegalArgumentException expected) { return; }
        throw new AssertionError(name);
    }
    private static Message message(long n) {
        return new Message(id(100+n), WORLD, EPISODE, SENDER, RECIPIENT,
            "source-report-"+n, "minecraft:overworld|4,100,1", 1, 1, 10, 11, 12);
    }
    private static void select(CommunicationJournal journal, Message message, UUID decision) {
        yes(journal.read(message.id(), message.recipient(), decision, 13), "policy read recorded");
        yes(journal.selected(message.id(), message.recipient(), decision, 14), "selection recorded");
    }

    private static void lifecycleAndReplay() {
        CommunicationJournal journal = new CommunicationJournal(8, 32);
        Message a = message(1), b = message(2);
        yes(journal.delivered(a), "delivered report recorded");
        yes(journal.delivered(a), "same delivery replay accepted");
        yes(journal.messages().size() == 1 && journal.events().size() == 1,
            "replaying delivery does not inflate communication count");
        Message conflicting = new Message(a.id(), WORLD, EPISODE, SENDER, RECIPIENT,
            a.reportId(), a.source(), 2, 1, 10, 11, 12);
        rejects(() -> journal.delivered(conflicting), "same identity different payload rejected");
        Message renamed = new Message(id(199), WORLD, EPISODE, SENDER, RECIPIENT,
            a.reportId(), a.source(), 1, 1, 10, 11, 12);
        rejects(() -> journal.delivered(renamed), "renamed duplicate delivery rejected");
        rejects(() -> journal.read(a.id(), OTHER, DECISION, 13), "counterfeit receiver cannot read");
        rejects(() -> journal.read(id(999), RECIPIENT, DECISION, 13), "unknown report cannot be read");
        rejects(() -> journal.read(a.id(), RECIPIENT, DECISION, 11), "read before delivery rejected");
        rejects(() -> journal.selected(a.id(), RECIPIENT, DECISION, 13), "selection without read rejected");
        rejects(() -> journal.assigned(a.id(), RECIPIENT, DECISION, JOB, 15), "assignment without selection rejected");
        rejects(() -> journal.completed(JOB, RECIPIENT, 16), "completion without assignment rejected");
        yes(journal.read(a.id(), RECIPIENT, DECISION, 13), "recipient policy actually read report");
        yes(journal.read(a.id(), RECIPIENT, DECISION, 13), "same read replay accepted");
        rejects(() -> journal.read(a.id(), RECIPIENT, DECISION, 14), "read timestamp cannot be rewritten");
        rejects(() -> journal.selected(a.id(), RECIPIENT, DECISION, 12), "selection before read rejected");
        yes(journal.delivered(b), "second candidate delivered");
        yes(journal.read(b.id(), RECIPIENT, DECISION, 14), "second candidate read");
        rejects(() -> journal.selected(a.id(), RECIPIENT, DECISION, 13),
            "selection cannot precede another input from same decision");
        yes(journal.selected(a.id(), RECIPIENT, DECISION, 14), "one candidate selected");
        yes(journal.selected(a.id(), RECIPIENT, DECISION, 14), "same selection replay accepted");
        rejects(() -> journal.selected(b.id(), RECIPIENT, DECISION, 14),
            "one decision cannot select two messages");
        rejects(() -> journal.assigned(b.id(), RECIPIENT, DECISION, JOB, 15),
            "unselected candidate cannot acquire job provenance");
        rejects(() -> journal.assigned(a.id(), RECIPIENT, DECISION, JOB, 13),
            "assignment before selection rejected");
        yes(journal.assigned(a.id(), RECIPIENT, DECISION, JOB, 15), "selected report bound to real job");
        yes(journal.assigned(a.id(), RECIPIENT, DECISION, JOB, 15), "assignment replay accepted");
        rejects(() -> journal.assigned(a.id(), RECIPIENT, DECISION, id(31), 15),
            "one decision cannot spawn another recorded job");
        rejects(() -> journal.completed(JOB, OTHER, 18), "another citizen cannot complete linked job");
        rejects(() -> journal.completed(JOB, RECIPIENT, 14), "physical completion cannot precede job");
        yes(journal.completed(JOB, RECIPIENT, 18), "trusted physical receipt recorded");
        yes(journal.completed(JOB, RECIPIENT, 18), "same physical receipt idempotent");
        rejects(() -> journal.completed(JOB, RECIPIENT, 19), "completion tick cannot be rewritten");
        yes(journal.events().stream().filter(e -> e.stage() == Stage.READ).count() == 2,
            "both inputs remain visible");
        yes(journal.events().stream().filter(e -> e.stage() == Stage.SELECTED).count() == 1,
            "read candidate is not treated as selected");
        yes(journal.events().stream().filter(e -> e.stage() == Stage.PHYSICAL_COMPLETED).count() == 1,
            "physical delivery counted once");

        Message c = message(3);
        yes(journal.delivered(c), "later candidate delivered");
        rejects(() -> journal.read(c.id(), RECIPIENT, DECISION, 19),
            "a completed decision cannot acquire retroactive inputs");
        select(journal, a, id(21));
        rejects(() -> journal.assigned(a.id(), RECIPIENT, id(21), JOB, 20),
            "job cannot be reused by another decision");
        yes(journal.assigned(a.id(), RECIPIENT, id(21), id(32), 20),
            "same report can inform a separate decision and job");
        for (int i = 0; i < journal.events().size(); i++)
            yes(journal.events().get(i).sequence() == i+1, "event sequence contiguous");
    }

    private static void scopeAndShape() {
        Message a = message(1);
        CommunicationJournal journal = new CommunicationJournal(8, 32);
        yes(journal.delivered(a), "first recipient delivery");
        Message otherRecipient = new Message(id(102), WORLD, EPISODE, SENDER, OTHER,
            a.reportId(), a.source(), 1, 1, 10, 11, 12);
        yes(journal.delivered(otherRecipient), "same source testimony may reach another recipient");
        yes(journal.read(a.id(), RECIPIENT, DECISION, 13), "decision scoped to first recipient");
        rejects(() -> journal.read(otherRecipient.id(), OTHER, DECISION, 13),
            "decision identity cannot cross recipients");
        Message otherEpisode = new Message(id(103), WORLD, id(99), SENDER, RECIPIENT,
            a.reportId(), a.source(), 1, 1, 10, 11, 12);
        yes(journal.delivered(otherEpisode), "separate episode may retain historical report identity");
        rejects(() -> journal.read(otherEpisode.id(), RECIPIENT, DECISION, 13),
            "decision cannot silently consume another episode");
        Message otherWorld = new Message(id(104), id(98), EPISODE, SENDER, RECIPIENT,
            a.reportId(), a.source(), 1, 1, 10, 11, 12);
        yes(journal.delivered(otherWorld), "world identity carried by every message");
        rejects(() -> journal.read(otherWorld.id(), RECIPIENT, DECISION, 13),
            "decision cannot cross worlds");
        rejects(() -> new Message(id(1), WORLD, EPISODE, SENDER, SENDER,
            "r", "s", 1, 1, 10, 11, 12), "self testimony is not inter-citizen communication");
        rejects(() -> new Message(id(1), WORLD, EPISODE, SENDER, RECIPIENT,
            " ", "s", 1, 1, 10, 11, 12), "blank report identity rejected");
        rejects(() -> new Message(id(1), WORLD, EPISODE, SENDER, RECIPIENT,
            "r", "s", 1, 1, 12, 11, 12), "send before observation rejected");
        rejects(() -> new Message(id(1), WORLD, EPISODE, SENDER, RECIPIENT,
            "r", "s", 1, 1, 10, 12, 11), "delivery before send rejected");
        rejects(() -> new Message(id(1), WORLD, EPISODE, SENDER, RECIPIENT,
            "r", "s", -1, 1, 10, 11, 12), "negative payload rejected");
        rejects(() -> new Event(0, Stage.DELIVERED, a.id(), RECIPIENT, null, null, 12),
            "event sequence starts at one");
        rejects(() -> new Event(1, Stage.DELIVERED, a.id(), RECIPIENT, DECISION, JOB, 12),
            "delivery does not imply action");
        rejects(() -> new Event(1, Stage.READ, a.id(), RECIPIENT, DECISION, JOB, 12),
            "read cannot imply assignment");
        rejects(() -> new Event(1, Stage.ASSIGNED, a.id(), RECIPIENT, DECISION, null, 12),
            "assignment must identify actual job");
        rejects(() -> new CommunicationJournal(0, 10), "positive message bound required");
        rejects(() -> new CommunicationJournal(10, 0), "positive event bound required");
    }

    private static void boundsAndPersistence() {
        Message a = message(1), b = message(2);
        CommunicationJournal bounded = new CommunicationJournal(1, 2);
        yes(bounded.delivered(a), "bounded delivery recorded");
        yes(!bounded.delivered(b), "message overflow is observational denial");
        yes(bounded.messages().equals(List.of(a)) && bounded.events().size() == 1,
            "message denial cannot leave a partial delivery");
        yes(bounded.read(a.id(), RECIPIENT, DECISION, 13), "remaining event slot usable");
        yes(!bounded.selected(a.id(), RECIPIENT, DECISION, 14), "event overflow visible");
        yes(bounded.events().size() == 2 && bounded.capacityDenials() == 2,
            "bounded history neither evicts nor hides its denials");
        yes(bounded.delivered(a) && bounded.read(a.id(), RECIPIENT, DECISION, 13),
            "idempotent replay succeeds even at capacity");
        yes(bounded.capacityDenials() == 2, "duplicates are not false capacity losses");
        rejects(() -> bounded.assigned(a.id(), RECIPIENT, DECISION, JOB, 15),
            "unrecorded selection cannot acquire downstream evidence");
        CommunicationJournal onlyOneEvent = new CommunicationJournal(2, 1);
        yes(onlyOneEvent.delivered(a), "one-event journal first delivery");
        yes(!onlyOneEvent.delivered(b) && onlyOneEvent.messages().size() == 1,
            "event denial cannot insert an unjournaled message");
        CommunicationJournal restored = CommunicationJournal.restore(1, 2,
            bounded.messages(), bounded.events(), bounded.capacityDenials());
        yes(restored.messages().equals(bounded.messages())
            && restored.events().equals(bounded.events()) && restored.capacityDenials() == 2,
            "capacity and partial lifecycle survive persistence exactly");

        CommunicationJournal complete = new CommunicationJournal(4, 20);
        complete.delivered(a);
        select(complete, a, DECISION);
        complete.assigned(a.id(), RECIPIENT, DECISION, JOB, 15);
        complete.completed(JOB, RECIPIENT, 18);
        CommunicationJournal roundTrip = CommunicationJournal.restore(4, 20,
            complete.messages(), complete.events(), 7);
        yes(roundTrip.events().equals(complete.events()), "full lifecycle round trip");
        yes(roundTrip.completed(JOB, RECIPIENT, 18) && roundTrip.events().size() == 5,
            "post-restore replay cannot double credit delivery");
        yes(roundTrip.capacityDenials() == 7, "lost-evidence count preserved");
        yes(roundTrip.delivered(b) && roundTrip.events().get(5).sequence() == 6,
            "append sequence resumes after restore");
        rejects(() -> CommunicationJournal.restore(4, 20, List.of(a,a), complete.events(), 0),
            "duplicate persisted message rejected");
        rejects(() -> CommunicationJournal.restore(4, 20, List.of(a,b), complete.events(), 0),
            "missing delivery event rejected");
        rejects(() -> CommunicationJournal.restore(4, 20, List.of(), complete.events(), 0),
            "orphan persisted events rejected");
        rejects(() -> CommunicationJournal.restore(4, 3, complete.messages(), complete.events(), 0),
            "over-capacity restored evidence rejected");
        rejects(() -> CommunicationJournal.restore(4, 20, complete.messages(), complete.events(), -1),
            "negative loss count rejected");
        List<Event> bad = new ArrayList<>(complete.events());
        bad.set(0, new Event(1, Stage.DELIVERED, a.id(), RECIPIENT, null, null, 99));
        rejects(() -> CommunicationJournal.restore(4, 20, List.of(a), bad, 0),
            "delivery event timestamp must match message");
        List<Event> reordered = new ArrayList<>(complete.events());
        reordered.set(1, complete.events().get(2));
        rejects(() -> CommunicationJournal.restore(4, 20, List.of(a), reordered, 0),
            "gapped or reordered sequence rejected");
        List<Event> counterfeit = new ArrayList<>(complete.events());
        counterfeit.set(4, new Event(5, Stage.PHYSICAL_COMPLETED, a.id(), OTHER, DECISION, JOB, 18));
        rejects(() -> CommunicationJournal.restore(4, 20, List.of(a), counterfeit, 0),
            "persistence cannot counterfeit physical actor");
        List<Event> duplicate = new ArrayList<>(complete.events());
        duplicate.add(new Event(6, Stage.PHYSICAL_COMPLETED, a.id(), RECIPIENT, DECISION, JOB, 18));
        rejects(() -> CommunicationJournal.restore(4, 20, List.of(a), duplicate, 0),
            "persisted duplicate receipt cannot inflate append count");
        try {
            complete.events().clear();
            throw new AssertionError("event snapshots mutable");
        } catch (UnsupportedOperationException expected) { checks++; }
        try {
            complete.messages().clear();
            throw new AssertionError("message snapshots mutable");
        } catch (UnsupportedOperationException expected) { checks++; }
    }

    public static void main(String[] args) {
        lifecycleAndReplay();
        scopeAndShape();
        boundsAndPersistence();
        System.out.println("PASS "+checks+" communication journal checks");
    }
}
