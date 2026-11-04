package dev.hearthbound.evidence;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/**
 * Pure Java 17 causal-history attention neural inference.
 * No Forge interfaces, inventory access, movement, or action execution.
 */
public final class CausalAttentionMlpParity {
    private static final int INPUT=16, HIDDEN=16, OUTPUT=4;
    private static final String HEADER="hearthbound.causal-attention-mlp-java.v1";
    private static final String FIXTURE_HEADER="hearthbound.causal-attention-mlp-java-fixtures.v1";
    private CausalAttentionMlpParity() {}

    private static String value(String raw,String name) {
        if(!raw.startsWith(name+"=")) throw new IllegalArgumentException("Expected "+name);
        return raw.substring(name.length()+1);
    }

    private static double[] numbers(String raw,String name,int count) {
        String[] parts=value(raw,name).split(",",-1);
        if(parts.length!=count) throw new IllegalArgumentException("Wrong "+name+" dimensions");
        double[] result=new double[count];
        for(int i=0;i<count;i++) {
            result[i]=Double.parseDouble(parts[i]);
            if(!Double.isFinite(result[i])) throw new IllegalArgumentException("Nonfinite "+name);
        }
        return result;
    }

    public record Frozen(double[] w1,double[] b1,double[] w2,double[] b2,String sha256) {
        public double[] scores(double[] x) {
            if(x.length!=INPUT) throw new IllegalArgumentException("Invalid attention vector");
            double[] hidden=new double[HIDDEN];
            for(int k=0;k<HIDDEN;k++) {
                double value=b1[k];
                for(int i=0;i<INPUT;i++) {
                    if(!Double.isFinite(x[i]))throw new IllegalArgumentException("Nonfinite feature");
                    value+=w1[k*INPUT+i]*x[i];
                }
                hidden[k]=Math.max(0.0,value);
            }
            double[] output=new double[OUTPUT];
            for(int j=0;j<OUTPUT;j++) {
                double value=b2[j];
                for(int k=0;k<HIDDEN;k++) value+=w2[j*HIDDEN+k]*hidden[k];
                output[j]=value;
            }
            return output;
        }

        /** Mask unregistered sources: zero-padding is never an action. */
        public int select(double[] x,int candidates) {
            if(candidates<1 || candidates>OUTPUT)
                throw new IllegalArgumentException("Invalid candidate budget");
            double[] scores=scores(x);
            int best=0;
            for(int j=1;j<candidates;j++) if(scores[j]>scores[best]) best=j;
            return best;
        }
    }

    public static Frozen read(Path file) throws Exception {
        List<String> lines=Files.readAllLines(file);
        if(lines.size()!=11 || !lines.get(0).equals(HEADER)
            || !lines.get(1).equals("origin=SIMULATED_CAUSAL_HISTORY_ONLY")
            || !lines.get(2).equals("features=unknown,last_observed_available,observation_age_norm,empirical_observed_change_rate")
            || !lines.get(3).equals("dimensions=16,16,4"))
            throw new IllegalArgumentException("Model schema incompatible");
        int seed=Integer.parseInt(value(lines.get(4),"training_seed"));
        int episodes=Integer.parseInt(value(lines.get(5),"training_episodes"));
        if(seed<0 || episodes<1)throw new IllegalArgumentException("Invalid training provenance");
        String digest=value(lines.get(6),"weights_sha256");
        if(!digest.matches("[a-f0-9]{64}"))throw new IllegalArgumentException("Invalid model digest");
        return new Frozen(numbers(lines.get(7),"w1",INPUT*HIDDEN),
            numbers(lines.get(8),"b1",HIDDEN),
            numbers(lines.get(9),"w2",HIDDEN*OUTPUT),
            numbers(lines.get(10),"b2",OUTPUT),digest);
    }

    public static int verify(Path weights,Path fixtures) throws Exception {
        Frozen model=read(weights);
        List<String> lines=Files.readAllLines(fixtures);
        if(lines.size()!=53 || !FIXTURE_HEADER.equals(lines.get(0))
            || !lines.get(1).equals("weights_sha256="+model.sha256()))
            throw new IllegalArgumentException("Incompatible test fixture");
        int index=0;
        for(String raw:lines.subList(2,lines.size())) {
            String[] columns=raw.split("\\|",-1);
            if(columns.length!=3 || Integer.parseInt(columns[0])!=index)
                throw new IllegalArgumentException("Unordered fixture");
            double[] features=numbers("x="+columns[1],"x",INPUT);
            double[] expected=numbers("scores="+columns[2],"scores",OUTPUT);
            double[] actual=model.scores(features);
            for(int j=0;j<OUTPUT;j++)
                if(Math.abs(expected[j]-actual[j])>1e-9)
                    throw new AssertionError("Python/Java mismatch fixture "+index+" source "+j);
            // Masked-choice validation uses a deterministic arbitrary candidate
            // prefix and checks that the chosen index cannot exceed that mask.
            int candidates=2+(index%3);
            int chosen=model.select(features,candidates);
            if(chosen<0 || chosen>=candidates)
                throw new AssertionError("Padded source chosen");
            index++;
        }
        if(index!=51)throw new IllegalArgumentException("Missing parity fixtures");
        return index;
    }

    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("Provide weights and fixtures");
        System.out.println("CAUSAL_ATTENTION_MLP_JAVA_PARITY_PASS fixtures="+
            verify(Path.of(args[0]),Path.of(args[1]))+
            " origin=SIMULATED_ONLY actions=false");
    }
}
