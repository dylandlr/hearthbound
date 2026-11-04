package dev.hearthbound.evidence;

import dev.hearthbound.world.CausalAttentionModel;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;

/** Verify the *production* read-only neural scorer against Python fixtures. */
public final class RealForgeAttentionModelParity {
    private RealForgeAttentionModelParity() {}
    public static void main(String[] args) throws Exception {
        if(args.length!=2)throw new IllegalArgumentException("model and fixtures required");
        CausalAttentionModel model=CausalAttentionModel.load(Path.of(args[0]));
        List<String> lines=Files.readAllLines(Path.of(args[1]));
        if(lines.size()!=53)throw new IllegalArgumentException("Missing fixture cases");
        int checked=0;
        for(String row:lines.subList(2,lines.size())) {
            String[] fields=row.split("\\|",-1);
            if(fields.length!=3)throw new IllegalArgumentException("Invalid case");
            String[] xs=fields[1].split(",",-1);
            String[] ys=fields[2].split(",",-1);
            if(xs.length!=16 || ys.length!=4)throw new IllegalArgumentException("Invalid dimension");
            double[] x=new double[16];
            for(int i=0;i<x.length;i++)x[i]=Double.parseDouble(xs[i]);
            double[] y=model.scores(x);
            for(int i=0;i<y.length;i++)
                if(Math.abs(y[i]-Double.parseDouble(ys[i]))>1e-9)
                    throw new AssertionError("Production neural scorer differs from Python");
            int n=2+(checked%3);
            if(model.select(x,n)>=n)
                throw new AssertionError("Production model selected padded source");
            checked++;
        }
        if(checked!=51)throw new AssertionError("Model case coverage");
        System.out.println("PRODUCTION_FORGE_NEURAL_ATTENTION_PARITY_PASS cases="+checked);
    }
}
