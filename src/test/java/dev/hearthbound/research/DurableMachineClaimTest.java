package dev.hearthbound.research;
import java.nio.file.Files;
import java.util.UUID;
public final class DurableMachineClaimTest {
    public static void main(String[] args) throws Exception {
        var dir=Files.createTempDirectory("machine-claim");
        var one=UUID.randomUUID();
        var op=UUID.randomUUID();
        var first=new DurableMachineClaim(dir);
        var claim=first.claim("world/overworld/mill/1",op,one);
        if (!claim.newlyCreated()) throw new AssertionError("Claim missing");
        var second=new DurableMachineClaim(dir);
        var recovered=second.recover("world/overworld/mill/1");
        if (!recovered.operationId().equals(op) || !recovered.citizenId().equals(one))
            throw new AssertionError("Claim identity lost after restart");
        if (second.claim("world/overworld/mill/1",op,one).newlyCreated())
            throw new AssertionError("Duplicate claim created");
        boolean blocked=false;
        try {second.claim("world/overworld/mill/1",UUID.randomUUID(),UUID.randomUUID());}
        catch (java.io.IOException expected) {blocked=true;}
        if (!blocked) throw new AssertionError("Different citizen stole millstone");
        if (!second.recover("world/overworld/mill/1").equals(recovered))
            throw new AssertionError("Conflicting claim changed machine owner");
        System.out.println("DurableMachineClaim: 5 checks passed");
    }
}
