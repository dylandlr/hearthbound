package dev.hearthbound.civilization;

import java.util.UUID;
import dev.hearthbound.civilization.ColonyTaskQueue.*;

public final class ColonyTaskQueueTest {
    static void check(boolean ok) { if (!ok) throw new AssertionError(); }
    public static void main(String[] args) {
        ColonyTaskQueue q = new ColonyTaskQueue();
        UUID a = UUID.randomUUID(), b = UUID.randomUUID(), job = UUID.randomUUID();
        q.enqueue("minecraft:overworld", 1, 2);
        q.enqueue("minecraft:overworld", 3, 4);
        Task first = q.reserve(a, "minecraft:overworld");
        Task second = q.reserve(b, "minecraft:overworld");
        check(first.id() != second.id());
        check(q.reserve(a, "minecraft:overworld") == null);
        q.assign(first.id(), a, job, 100);
        check(q.snapshot().get(0).state() == State.ASSIGNED);
        check(q.reserve(a, "minecraft:overworld") == null);
        q.finish(first.id(), a, job);
        check(q.snapshot().get(0).state() == State.DONE);
        check(q.reserve(a, "minecraft:overworld") == null);
        q.hold(second.id(), b);
        check(q.snapshot().get(1).state() == State.HELD);
        ColonyTaskQueue restored = new ColonyTaskQueue();
        for (Task t : q.snapshot()) restored.restore(t);
        check(restored.snapshot().equals(q.snapshot()));
        check(restored.enqueue("minecraft:overworld", 5, 6).id() == 3);
        boolean rejected = false;
        try { q.finish(second.id(), b, job); }
        catch (IllegalStateException expected) { rejected = true; }
        check(rejected);
        System.out.println("Colony task queue: PASS");
    }
}
