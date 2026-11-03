package dev.hearthbound.evidence;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

/**
 * Offline comparison on two additional physically observed Create mill states.
 * Runs solely on archived real RCON transcripts. No Minecraft control API.
 */
public final class RealMinecraftNeuralQContextReplay {
    private RealMinecraftNeuralQContextReplay() {}
    public static List<String> evaluate(Path weights,Path log,String arm) throws Exception {
        if(!arm.equals("SCRIPTED")&&!arm.equals("TRAINED_MLP"))
            throw new IllegalArgumentException("Unknown arm");
        var model=RealMinecraftNeuralQShadow.model(weights);
        var rows=new ArrayList<String>();
        var observed=new HashSet<String>();
        for(String line:Files.readAllLines(log)) {
            if(!line.startsWith("REAL_MILL_CONTEXT "))continue;
            var parts=line.split(" ");
            if(parts.length!=5 || !parts[4].equals("read_only=true"))
                throw new IllegalArgumentException("Malformed real mill context");
            String stage=key(parts[1],"stage"),reference=key(parts[2],"reference");
            String values=key(parts[3],"tensor");
            if(!observed.add(stage)) throw new IllegalArgumentException("Duplicate context");
            String required=switch(stage) {
                case "unpowered" -> "INSPECT_UNPOWERED";
                case "output_ready" -> "COLLECT_OUTPUT";
                default -> throw new IllegalArgumentException("Unexpected machine state");
            };
            if(!reference.equals(required)) throw new IllegalArgumentException("Wrong reference");
            String[] fields=values.split(",",-1);
            if(fields.length!=10)throw new IllegalArgumentException("Bad tensor width");
            double[] vector=new double[10];
            for(int i=0;i<10;i++)vector[i]=Double.parseDouble(fields[i]);
            if(stage.equals("unpowered") && vector[0]!=0.0)
                throw new IllegalArgumentException("Not unpowered");
            if(stage.equals("output_ready") && vector[2]!=1.0)
                throw new IllegalArgumentException("No flour observed");
            var q=model.evaluate(vector);
            int winner=0;
            for(int i=1;i<3;i++)if(q[i]>q[winner])winner=i;
            var gate=NeuralQContextGate.classify(vector,winner);
            if(gate!=NeuralQContextGate.Decision.ABSTAIN)
                throw new AssertionError("Neural context gate proposed unsupported gameplay action");
            rows.add("NEURAL_Q_MILL_CONTEXT arm="+arm+" stage="+stage
                +" reference="+reference+" gate=ABSTAIN neural_argmax="+winner
                +" checkpoint="+model.checksum()
                +" observation=REAL_MINECRAFT_REPLAY training=SIMULATED_ONLY"
                +" read_only=true dispatch=false");
        }
        if(!observed.equals(Set.of("unpowered","output_ready")))
            throw new IllegalArgumentException("Missing measured real-world contexts");
        return rows;
    }
    private static String key(String token,String name) {
        if(!token.startsWith(name+"="))throw new IllegalArgumentException("Missing "+name);
        return token.substring(name.length()+1);
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=3) throw new IllegalArgumentException("Need weights, RCON transcript and arm");
        for(String row:evaluate(Path.of(args[0]),Path.of(args[1]),args[2]))
            System.out.println(row);
    }
}
