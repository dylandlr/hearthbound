package dev.hearthbound.research;
import java.nio.file.Files;
import java.util.UUID;
public final class DurableCitizenWorkOrderTest {
    public static void main(String[] args) throws Exception {
        var dir=Files.createTempDirectory("citizen-work-order");
        var citizen=UUID.randomUUID();
        var first=new DurableCitizenWorkOrder(dir);
        var saved=first.prepare(citizen,"world/overworld/mill/1","create:milling/wheat",
                "world","minecraft:overworld","1,-59,1");
        if (!saved.newlyCreated()) throw new AssertionError("Work order not created");
        var restored=new DurableCitizenWorkOrder(dir);
        var recovered=restored.recover(citizen,"world/overworld/mill/1");
        if (!recovered.operationId().equals(saved.intent().operationId())
                || !recovered.citizenId().equals(citizen)
                || !recovered.recipeId().equals("create:milling/wheat"))
            throw new AssertionError("Work order identity changed across restart");
        if (restored.prepare(citizen,"world/overworld/mill/1","create:milling/wheat",
                "world","minecraft:overworld","1,-59,1").newlyCreated())
            throw new AssertionError("Duplicate work order created");
        boolean conflict=false;
        try {restored.prepare(citizen,"world/overworld/mill/1","create:milling/stone",
                "world","minecraft:overworld","1,-59,1");}
        catch (java.io.IOException expected) {conflict=true;}
        if (!conflict) throw new AssertionError("Conflicting work order accepted");
        boolean foreign=false;
        try {restored.recover(UUID.randomUUID(),"world/overworld/mill/1");}
        catch (java.io.IOException expected) {foreign=true;}
        if (!foreign) throw new AssertionError("Unowned work order recovered");
        System.out.println("DurableCitizenWorkOrder: 5 checks passed");
    }
}
