package dev.hearthbound.research;
import java.util.UUID;
public final class MachineClaimRetirementGateTest {
    public static void main(String[] args) {
        UUID op=UUID.randomUUID(), citizen=UUID.randomUUID();
        var claim=new DurableMachineClaim.Claim(UUID.randomUUID(),op,citizen,"millstone/one");
        var good=new MachineClaimRetirementGate.Evidence(op,citizen,true,true,true,true,true,false);
        if (MachineClaimRetirementGate.evaluate(claim,good)!=MachineClaimRetirementGate.Decision.ELIGIBLE_FOR_RETIREMENT)
            throw new AssertionError("Verified claim must be eligible");
        var cases=new MachineClaimRetirementGate.Evidence[]{
            new MachineClaimRetirementGate.Evidence(UUID.randomUUID(),citizen,true,true,true,true,true,false),
            new MachineClaimRetirementGate.Evidence(op,UUID.randomUUID(),true,true,true,true,true,false),
            new MachineClaimRetirementGate.Evidence(op,citizen,false,true,true,true,true,false),
            new MachineClaimRetirementGate.Evidence(op,citizen,true,false,true,true,true,false),
            new MachineClaimRetirementGate.Evidence(op,citizen,true,true,false,true,true,false),
            new MachineClaimRetirementGate.Evidence(op,citizen,true,true,true,false,true,false),
            new MachineClaimRetirementGate.Evidence(op,citizen,true,true,true,true,false,false),
            new MachineClaimRetirementGate.Evidence(op,citizen,true,true,true,true,true,true)
        };
        for(var e:cases)
            if(MachineClaimRetirementGate.evaluate(claim,e)!=MachineClaimRetirementGate.Decision.KEEP_CLAIM)
                throw new AssertionError("Unsafe machine retirement");
        if(MachineClaimRetirementGate.evaluate(null,good)!=MachineClaimRetirementGate.Decision.KEEP_CLAIM)
            throw new AssertionError("Missing claim retired");
        System.out.println("MachineClaimRetirementGate: 10 checks passed");
    }
}
