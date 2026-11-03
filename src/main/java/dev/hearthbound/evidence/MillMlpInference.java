package dev.hearthbound.evidence;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

/**
 * Deterministic Java 17 inference for a supervised imitation MLP, 5-12-4.
 * It does not execute Minecraft actions or update weights from experience.
 */
public final class MillMlpInference {
    public static final String RESOURCE = "/hearthbound/policy/mill-mlp-v1.txt";
    public static final String SHA256 = "219cb6ba467777f4f2246a538e2c2aa7bb49cba6e552a9ec714bbc2e2e064f6e";
    public enum Action {
        INSPECT_UNPOWERED, COLLECT_OUTPUT, WAIT_FOR_PROCESSING, REQUEST_WHEAT_HAUL
    }
    private final double[] w1, b1, w2, b2;

    private MillMlpInference(double[] w1, double[] b1, double[] w2, double[] b2) {
        this.w1=w1; this.b1=b1; this.w2=w2; this.b2=b2;
    }

    public static MillMlpInference loadBundled() {
        try (InputStream stream=MillMlpInference.class.getResourceAsStream(RESOURCE)) {
            if (stream==null) throw new IllegalStateException("Missing bundled MLP weights");
            return parse(stream.readAllBytes());
        } catch (IOException error) {
            throw new IllegalStateException("Cannot load bundled MLP weights",error);
        }
    }

    public static MillMlpInference parse(byte[] bytes) {
        try {
            String digest=HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
            if (!SHA256.equals(digest)) throw new IllegalArgumentException("MLP weight checksum mismatch");
        } catch (NoSuchAlgorithmException error) {
            throw new IllegalStateException("SHA-256 unavailable", error);
        }
        String[] lines=new String(bytes, StandardCharsets.UTF_8).strip().split("\\R");
        if (lines.length!=8 || !lines[0].equals("hearthbound.mill-mlp.v1")
                || !lines[1].equals("features=powered,wheat_present,flour_present,blocked,experience_norm")
                || !lines[2].equals("actions=INSPECT_UNPOWERED,COLLECT_OUTPUT,WAIT_FOR_PROCESSING,REQUEST_WHEAT_HAUL")
                || !lines[3].equals("hidden=12"))
            throw new IllegalArgumentException("Unexpected inference contract");
        return new MillMlpInference(values(lines[4],"w1",60),values(lines[5],"b1",12),
                                    values(lines[6],"w2",48),values(lines[7],"b2",4));
    }

    private static double[] values(String line,String key,int length) {
        if (!line.startsWith(key+"=")) throw new IllegalArgumentException("Missing "+key);
        String[] parts=line.substring(key.length()+1).split(",");
        if (parts.length!=length) throw new IllegalArgumentException("Bad "+key+" length");
        double[] result=new double[length];
        for (int i=0;i<length;i++) {
            result[i]=Double.parseDouble(parts[i]);
            if (!Double.isFinite(result[i])) throw new IllegalArgumentException("Nonfinite model weight");
        }
        return result;
    }

    public Action predict(boolean powered,boolean wheat,boolean flour,
                          boolean blocked,long verifiedExperience) {
        double[] input={powered?1:0,wheat?1:0,flour?1:0,blocked?1:0,
                        Math.min(verifiedExperience,10L)/10.0};
        if (verifiedExperience<0) throw new IllegalArgumentException("Negative experience");
        double[] hidden=new double[12];
        for (int h=0;h<12;h++) {
            double sum=b1[h];
            for (int i=0;i<5;i++) sum+=w1[h*5+i]*input[i];
            hidden[h]=Math.max(0,sum);
        }
        double maximum=Double.NEGATIVE_INFINITY;
        int selected=-1;
        for (int o=0;o<4;o++) {
            double score=b2[o];
            for(int h=0;h<12;h++) score+=w2[o*12+h]*hidden[h];
            if(score>maximum) {maximum=score;selected=o;}
        }
        return Action.values()[selected];
    }
}
