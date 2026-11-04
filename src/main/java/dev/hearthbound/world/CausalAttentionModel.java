package dev.hearthbound.world;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.List;

/** Fixed-shape simulator-trained attention inference: no world or inventory API. */
public final class CausalAttentionModel {
    public static final String SCHEMA="hearthbound.causal-attention-mlp-java.v1";
    private static final int INPUT=16, HIDDEN=16, OUTPUT=4;
    private final double[] w1,b1,w2,b2;
    private final String fileSha256;

    private CausalAttentionModel(double[] w1,double[] b1,double[] w2,double[] b2,String hash) {
        this.w1=w1;this.b1=b1;this.w2=w2;this.b2=b2;this.fileSha256=hash;
    }

    private static String field(String line,String name) {
        if(!line.startsWith(name+"="))throw new IllegalArgumentException("Invalid "+name);
        return line.substring(name.length()+1);
    }
    private static double[] parse(String line,String name,int size) {
        String[] parts=field(line,name).split(",",-1);
        if(parts.length!=size)throw new IllegalArgumentException("Invalid tensor size: "+name);
        double[] values=new double[size];
        for(int i=0;i<size;i++) {
            values[i]=Double.parseDouble(parts[i]);
            if(!Double.isFinite(values[i]))throw new IllegalArgumentException("Non-finite tensor");
        }
        return values;
    }

    public static CausalAttentionModel load(Path file) throws Exception {
        byte[] data=Files.readAllBytes(file);
        if(data.length<100 || data.length>200000)
            throw new IllegalArgumentException("Invalid bounded model file");
        List<String> lines=Files.readAllLines(file);
        if(lines.size()!=11 || !SCHEMA.equals(lines.get(0))
            || !"origin=SIMULATED_CAUSAL_HISTORY_ONLY".equals(lines.get(1))
            || !"features=unknown,last_observed_available,observation_age_norm,empirical_observed_change_rate".equals(lines.get(2))
            || !"dimensions=16,16,4".equals(lines.get(3))
            || Integer.parseInt(field(lines.get(5),"training_episodes"))<1
            || !field(lines.get(6),"weights_sha256").matches("[a-f0-9]{64}"))
            throw new IllegalArgumentException("Incompatible model provenance");
        Integer.parseInt(field(lines.get(4),"training_seed"));
        byte[] sha=MessageDigest.getInstance("SHA-256").digest(data);
        StringBuilder fingerprint=new StringBuilder();
        for(byte part:sha)fingerprint.append(String.format("%02x",part&255));
        return new CausalAttentionModel(parse(lines.get(7),"w1",INPUT*HIDDEN),
            parse(lines.get(8),"b1",HIDDEN),parse(lines.get(9),"w2",HIDDEN*OUTPUT),
            parse(lines.get(10),"b2",OUTPUT),fingerprint.toString());
    }

    public String sha256() {return fileSha256;}

    public double[] scores(double[] features) {
        if(features.length!=INPUT)throw new IllegalArgumentException("Invalid attention observation width");
        for(double x:features)if(!Double.isFinite(x))throw new IllegalArgumentException("Non-finite feature");
        double[] hidden=new double[HIDDEN];
        for(int j=0;j<HIDDEN;j++) {
            double v=b1[j];
            for(int k=0;k<INPUT;k++)v+=w1[j*INPUT+k]*features[k];
            hidden[j]=Math.max(0.,v);
        }
        double[] values=new double[OUTPUT];
        for(int j=0;j<OUTPUT;j++) {
            double v=b2[j];
            for(int k=0;k<HIDDEN;k++)v+=w2[j*HIDDEN+k]*hidden[k];
            if(!Double.isFinite(v))throw new IllegalArgumentException("Non-finite network output");
            values[j]=v;
        }
        return values;
    }

    public int select(double[] features,int candidates) {
        if(candidates<1 || candidates>OUTPUT)
            throw new IllegalArgumentException("Invalid candidate count");
        double[] values=scores(features);
        int chosen=0;
        for(int i=1;i<candidates;i++)if(values[i]>values[chosen])chosen=i;
        return chosen;
    }
}
