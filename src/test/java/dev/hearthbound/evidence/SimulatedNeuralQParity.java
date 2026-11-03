package dev.hearthbound.evidence;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.List;

/** Pure Java 17 parity verifier; never connects to or controls Minecraft. */
public final class SimulatedNeuralQParity {
    private static final int INPUT=10, HIDDEN=20, OUTPUT=3;
    private static final String HEADER="hearthbound.simulated-neural-q-java-parity.v1";
    private SimulatedNeuralQParity() {}

    private static double[] parse(String line, String name, int length) {
        if (!line.startsWith(name+"=")) throw new IllegalArgumentException("Missing "+name);
        String[] parts=line.substring(name.length()+1).split(",",-1);
        if (parts.length!=length) throw new IllegalArgumentException("Wrong "+name+" length");
        double[] values=new double[length];
        for (int i=0;i<length;i++) {
            values[i]=Double.parseDouble(parts[i]);
            if (!Double.isFinite(values[i])) throw new IllegalArgumentException("Nonfinite "+name);
        }
        return values;
    }

    private static double[] values(double[] input, double[] w1, double[] b1,
                                   double[] w2, double[] b2) {
        double[] h=new double[HIDDEN];
        for (int j=0;j<HIDDEN;j++) {
            double sum=b1[j];
            for (int k=0;k<INPUT;k++) sum+=w1[j*INPUT+k]*input[k];
            h[j]=Math.max(0.,sum);
        }
        double[] q=new double[OUTPUT];
        for (int j=0;j<OUTPUT;j++) {
            double sum=b2[j];
            for (int k=0;k<HIDDEN;k++) sum+=w2[j*HIDDEN+k]*h[k];
            q[j]=sum;
        }
        return q;
    }

    private static String after(String line,String key) {
        if (!line.startsWith(key+"="))throw new IllegalArgumentException("Missing "+key);
        return line.substring(key.length()+1);
    }

    public static int check(Path weights, Path fixtures) throws Exception {
        List<String> model=Files.readAllLines(weights);
        List<String> cases=Files.readAllLines(fixtures);
        if(model.size()!=10 || !HEADER.equals(model.get(0))
            || !"observation_schema=hearthbound.mill-observation.v2".equals(model.get(1))
            || !"features=powered,mill_wheat_present,mill_flour_present,mill_blocked,verified_experience_norm,source_unknown,source_empty,source_available,task_active,source_stale".equals(model.get(2))
            || !"actions=INSPECT_SOURCE,WAIT_FOR_SUPPLY,REQUEST_WHEAT_HAUL".equals(model.get(3))
            || !"dimensions=10,20,3".equals(model.get(4)))
            throw new IllegalArgumentException("Wrong model/schema/action contract");
        String digest=after(model.get(5),"checkpoint_sha256");
        if (!digest.matches("[a-f0-9]{64}")
            || cases.size()<3
            || !"hearthbound.simulated-neural-q-parity-fixtures.v1".equals(cases.get(0))
            || !cases.get(1).equals("checkpoint_sha256="+digest))
            throw new IllegalArgumentException("Missing or mismatched model provenance");
        double[] w1=parse(model.get(6),"w1",INPUT*HIDDEN);
        double[] b1=parse(model.get(7),"b1",HIDDEN);
        double[] w2=parse(model.get(8),"w2",HIDDEN*OUTPUT);
        double[] b2=parse(model.get(9),"b2",OUTPUT);
        int checked=0;
        for(String line:cases.subList(2,cases.size())) {
            String[] parts=line.split("\\|",-1);
            if (parts.length!=4 || parts[0].isBlank())
                throw new IllegalArgumentException("Bad fixture row");
            double[] x=parse("x="+parts[1],"x",INPUT);
            double[] expected=parse("q="+parts[2],"q",OUTPUT);
            int action=Integer.parseInt(parts[3]);
            if (action<0 || action>=OUTPUT) throw new IllegalArgumentException("Invalid action");
            double[] observed=values(x,w1,b1,w2,b2);
            int argmax=0;
            for(int i=0;i<OUTPUT;i++) {
                if (Math.abs(observed[i]-expected[i])>1e-9)
                    throw new AssertionError(parts[0]+" Q["+i+"] Java="+observed[i]+" Python="+expected[i]);
                if (observed[i]>observed[argmax]) argmax=i;
            }
            if(argmax!=action) throw new AssertionError("Action parity failure "+parts[0]);
            checked++;
        }
        if(checked!=48) throw new IllegalArgumentException("Expected 48 parity fixtures");
        return checked;
    }
    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("Need model weights and parity fixtures");
        int count=check(Path.of(args[0]),Path.of(args[1]));
        System.out.println("PASS "+count+" Python/Java neural Q score and action parity fixtures (SIMULATED_ONLY)");
    }
}
