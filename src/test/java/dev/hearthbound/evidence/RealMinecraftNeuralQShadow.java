package dev.hearthbound.evidence;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;
import java.util.regex.*;

/**
 * Offline/read-only Java neural Q shadow over real Minecraft RCON transcripts.
 * Consumes archived source observations; has no Minecraft classes or commands.
 * Simulator-trained weights are never permitted to dispatch game actions.
 */
public final class RealMinecraftNeuralQShadow {
    private static final String[] ACTIONS={
        "INSPECT_SOURCE","WAIT_FOR_SUPPLY","REQUEST_WHEAT_HAUL"
    };
    private static final Pattern VECTOR=Pattern.compile(
        "^REAL_OBSERVATION_V2 stage=(empty|unknown|available) schema=hearthbound\\.mill-observation\\.v2 tensor=([0-9.,]+)$");
    private static final Pattern REFERENCE=Pattern.compile(
        "^REAL_SOURCE_PLAN stage=(empty|unknown|available) action=([A-Z_]+) source=([A-Z]+) read_only=true$");
    private static final List<String> STAGES=List.of("empty","unknown","available");

    private RealMinecraftNeuralQShadow() {}

    private static double[] parse(String s,int size) {
        String[] parts=s.split(",",-1);
        if(parts.length!=size)throw new IllegalArgumentException("Bad vector length");
        double[] x=new double[size];
        for(int i=0;i<size;i++) {
            x[i]=Double.parseDouble(parts[i]);
            if(!Double.isFinite(x[i]))throw new IllegalArgumentException("Nonfinite value");
        }
        return x;
    }
    private static String field(String line,String key) {
        if(!line.startsWith(key+"="))throw new IllegalArgumentException("Expected "+key);
        return line.substring(key.length()+1);
    }

    static Model model(Path path) throws Exception {
        var lines=Files.readAllLines(path);
        if(lines.size()!=10
            || !lines.get(0).equals("hearthbound.simulated-neural-q-java-parity.v1")
            || !lines.get(1).equals("observation_schema=hearthbound.mill-observation.v2")
            || !lines.get(2).equals("features=powered,mill_wheat_present,mill_flour_present,mill_blocked,verified_experience_norm,source_unknown,source_empty,source_available,task_active,source_stale")
            || !lines.get(3).equals("actions=INSPECT_SOURCE,WAIT_FOR_SUPPLY,REQUEST_WHEAT_HAUL")
            || !lines.get(4).equals("dimensions=10,20,3"))
            throw new IllegalArgumentException("Wrong model schema/order/dimensions");
        String digest=field(lines.get(5),"checkpoint_sha256");
        if(!digest.matches("[a-f0-9]{64}"))throw new IllegalArgumentException("No checkpoint provenance");
        return new Model(digest,parse(field(lines.get(6),"w1"),200),
                         parse(field(lines.get(7),"b1"),20),
                         parse(field(lines.get(8),"w2"),60),
                         parse(field(lines.get(9),"b2"),3));
    }
    record Model(String checksum,double[] w1,double[] b1,double[] w2,double[] b2) {
        double[] evaluate(double[] input) {
            double[] h=new double[20];
            for(int i=0;i<20;i++) {
                double sum=b1[i];
                for(int j=0;j<10;j++)sum+=w1[i*10+j]*input[j];
                h[i]=Math.max(0.,sum);
            }
            double[] q=new double[3];
            for(int i=0;i<3;i++) {
                double sum=b2[i];
                for(int j=0;j<20;j++)sum+=w2[i*20+j]*h[j];
                q[i]=sum;
            }
            return q;
        }
    }
    private static Map<String,double[]> observations(List<String> lines) {
        var result=new LinkedHashMap<String,double[]>();
        for(String line:lines) {
            if(!line.contains("REAL_OBSERVATION_V2"))continue;
            var m=VECTOR.matcher(line.strip());
            if(!m.matches()||result.containsKey(m.group(1)))
                throw new IllegalArgumentException("Malformed/duplicate Minecraft tensor");
            double[] x=parse(m.group(2),10);
            int state=STAGES.indexOf(m.group(1));
            // empty index 0 => one-hot [0,1,0]; unknown => [1,0,0]; available => [0,0,1].
            for(int j=0;j<3;j++) {
                int selected=switch(state) {
                    case 0 -> 1;
                    case 1 -> 0;
                    default -> 2;
                };
                if(x[5+j]!=(j==selected?1.:0.))
                    throw new IllegalArgumentException("Incorrect live resource mask");
            }
            if(x[0]!=1. || x[1]!=0. || x[2]!=0. || x[8]!=0. || x[9]!=0.)
                throw new IllegalArgumentException("Not fresh idle powered mill");
            result.put(m.group(1),x);
        }
        if(!result.keySet().containsAll(STAGES)||result.size()!=3)
            throw new IllegalArgumentException("Incomplete real Minecraft source states");
        return result;
    }
    private static Map<String,String> references(List<String> lines) {
        var result=new HashMap<String,String>();
        for(String line:lines) {
            if(!line.contains("REAL_SOURCE_PLAN"))continue;
            var m=REFERENCE.matcher(line.strip());
            if(!m.matches()||result.containsKey(m.group(1)))
                throw new IllegalArgumentException("Malformed/duplicate reference plan");
            String stage=m.group(1);
            String expected=switch(stage) {
                case "empty"->"WAIT_FOR_SUPPLY";
                case "unknown"->"INSPECT_SOURCE";
                default->"REQUEST_WHEAT_HAUL";
            };
            if(!m.group(2).equals(expected)||!m.group(3).equals(stage.toUpperCase(Locale.ROOT)))
                throw new IllegalArgumentException("Reference plan mismatch");
            result.put(stage,m.group(2));
        }
        if(result.size()!=3)throw new IllegalArgumentException("Missing real reference decisions");
        return result;
    }
    public static List<String> shadow(Path weights,Path rcon,String arm) throws Exception {
        if(!arm.equals("SCRIPTED") && !arm.equals("TRAINED_MLP"))
            throw new IllegalArgumentException("Unknown live policy arm");
        var m=model(weights);
        var lines=Files.readAllLines(rcon);
        var inputs=observations(lines);
        var baselines=references(lines);
        var result=new ArrayList<String>();
        for(String stage:STAGES) {
            var q=m.evaluate(inputs.get(stage));
            int choice=0;
            for(int i=1;i<3;i++)if(q[i]>q[choice])choice=i;
            String label=ACTIONS[choice];
            String row="NEURAL_Q_REAL_SHADOW arm="+arm+" stage="+stage
                +" neural="+label+" reference="+baselines.get(stage)
                +" q="+q[0]+","+q[1]+","+q[2]
                +" checkpoint="+m.checksum
                +" simulator_trained=true read_only=true dispatch=false";
            result.add(row);
        }
        return result;
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=3)throw new IllegalArgumentException("Need model, real RCON log, arm");
        for(String row:shadow(Path.of(args[0]),Path.of(args[1]),args[2]))
            System.out.println(row);
    }
}
