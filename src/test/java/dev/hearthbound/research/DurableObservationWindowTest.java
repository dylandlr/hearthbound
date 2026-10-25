package dev.hearthbound.research;
import java.nio.file.Files;
import java.util.UUID;
public final class DurableObservationWindowTest {
    public static void main(String[] args) throws Exception {
        var root=Files.createTempDirectory("observation-window");
        Files.createDirectory(root.resolve("starts"));Files.createDirectory(root.resolve("ends"));
        UUID op=UUID.randomUUID(),citizen=UUID.randomUUID();
        var writer=new DurableObservationWindow(root.resolve("starts"),root.resolve("ends"));
        writer.begin(op,citizen,"world/mill/1",100);
        boolean refused=false;
        try {writer.recovered(op);}catch(java.io.IOException expected){refused=true;}
        if(!refused)throw new AssertionError("Incomplete window accepted");
        if(!writer.complete(op,citizen,"world/mill/1",155))
            throw new AssertionError("Completion missing");
        var reload=new DurableObservationWindow(root.resolve("starts"),root.resolve("ends"));
        var window=reload.recovered(op);
        if(window.startTick()!=100||window.endTick()!=155||!window.citizenId().equals(citizen))
            throw new AssertionError("Window changed after restart");
        if(reload.complete(op,citizen,"world/mill/1",155))
            throw new AssertionError("Duplicate completion");
        refused=false;
        try {reload.complete(op,citizen,"world/mill/1",156);}
        catch(java.io.IOException expected){refused=true;}
        if(!refused)throw new AssertionError("Conflicting completion accepted");
        refused=false;
        try {reload.complete(op,UUID.randomUUID(),"world/mill/1",155);}
        catch(java.io.IOException expected){refused=true;}
        if(!refused)throw new AssertionError("Foreign citizen completion accepted");
        System.out.println("DurableObservationWindow: 6 checks passed");
    }
}
