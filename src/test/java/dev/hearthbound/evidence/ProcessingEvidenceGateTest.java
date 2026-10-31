package dev.hearthbound.evidence;

import java.util.ArrayList;
import java.util.List;
import dev.hearthbound.evidence.ProcessingEvidenceGate.*;

public final class ProcessingEvidenceGateTest {
    static Receipt sample(String id) { return new Receipt(id,"minecraft:overworld","mill@0,64,0",
            "create:milling/wheat","minecraft:wheat","create:wheat_flour",8,7,0,1,100,120,true,true); }
    static int checks = 0;
    static void expect(boolean value, String msg) { checks++; if (!value) throw new AssertionError(msg); }
    public static void main(String[] ignored) {
        List<String> credited = new ArrayList<>();
        ProcessingEvidenceGate gate = new ProcessingEvidenceGate(r -> credited.add(r.eventId()));
        expect(gate.submit(sample("e1")) == Result.ACCEPTED,"real mill receipt");
        expect(gate.submit(sample("e1")) == Result.DUPLICATE,"duplicate");
        expect(credited.size() == 1,"exactly once in-memory");
        Receipt base = sample("e2");
        expect(gate.submit(new Receipt("e2",base.dimension(),base.machineId(),base.recipeId(),base.inputItem(),base.outputItem(),8,8,0,1,100,120,true,true)) == Result.UNVERIFIED,"no input consumption");
        expect(gate.submit(new Receipt("e2",base.dimension(),base.machineId(),base.recipeId(),base.inputItem(),base.outputItem(),8,7,0,0,100,120,true,true)) == Result.UNVERIFIED,"no output");
        expect(gate.submit(new Receipt("e2",base.dimension(),base.machineId(),base.recipeId(),base.inputItem(),base.outputItem(),8,7,0,1,100,120,false,true)) == Result.UNVERIFIED,"unloaded machine");
        expect(gate.submit(new Receipt("e2",base.dimension(),base.machineId(),base.recipeId(),base.inputItem(),base.outputItem(),8,7,0,1,100,120,true,false)) == Result.UNVERIFIED,"not server observed");
        expect(gate.submit(new Receipt("e2",base.dimension(),base.machineId(),base.recipeId(),base.inputItem(),base.outputItem(),8,7,0,1,120,120,true,true)) == Result.INVALID,"zero duration");
        expect(gate.submit(sample("e2")) == Result.ACCEPTED,"failed receipt not consuming ID");
        ProcessingEvidenceGate restored = new ProcessingEvidenceGate(r -> credited.add(r.eventId()));
        restored.restoreCommitted(List.of("e1","e2"));
        expect(restored.submit(sample("e1")) == Result.DUPLICATE,"restart restore prevents replay");
        ProcessingEvidenceGate failing = new ProcessingEvidenceGate(r -> { throw new IllegalStateException("storage down"); });
        boolean threw = false;
        try { failing.submit(sample("retry")); } catch(IllegalStateException e) { threw = true; }
        expect(threw,"failure propagated");
        expect(failing.submit(null) == Result.INVALID,"null receipt");
        System.out.println("PASS " + checks + " checks");
    }
}
