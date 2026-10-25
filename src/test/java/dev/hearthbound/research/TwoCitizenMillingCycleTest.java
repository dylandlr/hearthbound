package dev.hearthbound.research;

import java.nio.file.Files;
import java.util.UUID;

/**
 * Contract-scale two-generation milling experiment: distinct operation IDs,
 * distinct citizen attribution, one exclusive machine. Not a Forge GameTest.
 */
public final class TwoCitizenMillingCycleTest {
    private static final String MACHINE = "world/overworld/millstone/1";
    private static final String RECIPE = "create:milling/wheat";

    private static CitizenDiscoveryGate.Assignment assignment(UUID op, UUID citizen) {
        return new CitizenDiscoveryGate.Assignment(op,citizen,"world","minecraft:overworld",
                "1,-59,1",RECIPE,true);
    }
    private static CitizenDiscoveryGate.Observation observed(UUID op) {
        return new CitizenDiscoveryGate.Observation(op,"world","minecraft:overworld",
                "1,-59,1",RECIPE,RECIPE,1,true,true);
    }
    public static void main(String[] args) throws Exception {
        var root=Files.createTempDirectory("hearthbound-two-citizen-");
        Files.createDirectory(root.resolve("claims"));
        Files.createDirectory(root.resolve("credits"));
        UUID a=UUID.randomUUID(), b=UUID.randomUUID();
        UUID opA=UUID.randomUUID(), opB=UUID.randomUUID();
        var claims=new DurableMachineHandoff(root.resolve("claims"));
        var credits=new CitizenDiscoveryCommitter(root.resolve("credits"));

        claims.acquire(MACHINE,opA,a);
        if(!credits.commit(assignment(opA,a),observed(opA),"receipt:A").newlyCredited())
            throw new AssertionError("First citizen not credited");
        boolean conflict=false;
        try {claims.acquire(MACHINE,opB,b);}
        catch(java.io.IOException expected){conflict=true;}
        if(!conflict)throw new AssertionError("Second owner acquired active machine");

        var recovered=new DurableMachineHandoff(root.resolve("claims"));
        var first=recovered.current(MACHINE);
        if(first==null || first.owner().generation()!=1 || first.retired())
            throw new AssertionError("Generation 1 not durable");
        recovered.retire(MACHINE,opA,a,MachineClaimRetirementGate.Decision.ELIGIBLE_FOR_RETIREMENT);
        recovered.acquire(MACHINE,opB,b);

        var creditsAfterRestart=new CitizenDiscoveryCommitter(root.resolve("credits"));
        if(!creditsAfterRestart.commit(assignment(opB,b),observed(opB),"receipt:B").newlyCredited())
            throw new AssertionError("Second citizen not credited");
        if(creditsAfterRestart.balance(a)!=1 || creditsAfterRestart.balance(b)!=1)
            throw new AssertionError("Citizen credit leaked between owners");
        if(creditsAfterRestart.commit(assignment(opA,a),observed(opA),"receipt:A").newlyCredited()
                || creditsAfterRestart.commit(assignment(opB,b),observed(opB),"receipt:B").newlyCredited())
            throw new AssertionError("Duplicate operation credited");
        conflict=false;
        try {creditsAfterRestart.commit(assignment(opB,a),observed(opB),"receipt:B");}
        catch(java.io.IOException expected){conflict=true;}
        if(!conflict || creditsAfterRestart.balance(a)!=1 || creditsAfterRestart.balance(b)!=1)
            throw new AssertionError("Same operation reassigned to another citizen");

        var generationTwo=new DurableMachineHandoff(root.resolve("claims")).current(MACHINE);
        if(generationTwo==null || generationTwo.retired()
                || generationTwo.owner().generation()!=2 || !generationTwo.owner().citizen().equals(b))
            throw new AssertionError("Generation 2 ownership lost");
        System.out.println("TwoCitizenMillingCycle: 8 checks passed (contract only)");
    }
}
