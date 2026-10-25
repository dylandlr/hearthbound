package dev.hearthbound.research;
import java.nio.file.Files;
import java.util.UUID;
public final class DurableMachineHandoffTest {
    public static void main(String[] args) throws Exception {
        var dir=Files.createTempDirectory("machine-handoff");
        var first=new DurableMachineHandoff(dir);
        UUID opA=UUID.randomUUID(),a=UUID.randomUUID(),opB=UUID.randomUUID(),b=UUID.randomUUID();
        var acquired=first.acquire("mill/1",opA,a);
        if(acquired.owner().generation()!=1 || acquired.retired())throw new AssertionError("Initial claim");
        if(!first.acquire("mill/1",opA,a).equals(acquired))throw new AssertionError("Replay");
        boolean rejected=false;
        try {first.acquire("mill/1",opB,b);}catch(java.io.IOException expected){rejected=true;}
        if(!rejected)throw new AssertionError("Overlapping owner");
        var restarted=new DurableMachineHandoff(dir);
        if(!restarted.current("mill/1").equals(acquired))throw new AssertionError("Crash reload");
        rejected=false;
        try {restarted.retire("mill/1",opA,a,MachineClaimRetirementGate.Decision.KEEP_CLAIM);}
        catch(java.io.IOException expected){rejected=true;}
        if(!rejected)throw new AssertionError("Unsafe retirement");
        restarted.retire("mill/1",opA,a,MachineClaimRetirementGate.Decision.ELIGIBLE_FOR_RETIREMENT);
        var next=new DurableMachineHandoff(dir).acquire("mill/1",opB,b);
        if(next.owner().generation()!=2 || !next.owner().citizen().equals(b))
            throw new AssertionError("Handoff generation");
        rejected=false;
        try {restarted.retire("mill/1",opA,a,MachineClaimRetirementGate.Decision.ELIGIBLE_FOR_RETIREMENT);}
        catch(java.io.IOException expected){rejected=true;}
        if(!rejected)throw new AssertionError("Old owner retired next owner");
        System.out.println("DurableMachineHandoff: 7 checks passed");
    }
}
