package dev.hearthbound.civilization;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.UUID;

/** Private execution-cost learning over authored, recipe-grounded capabilities.
 * This is contextual RLS, not a deep network or an occupation assignment. */
public final class VillageWorkPolicy {
    public enum Kind { HARVEST_REPLANT, MILL_FLOUR, PREPARE_DOUGH, BAKE_BREAD, REFILL_WATER, EAT_BREAD, OBSERVE, WAIT }
    public static final String SCHEMA = "hearthbound.village-work.v0.23";
    public static final int MAX_OUTCOMES = 4096;
    public record Offer(String id, UUID citizen, Kind kind, double distance, double deficit, double age,
                        double hunger, String evidence, long site, long auxiliary) {
        public Offer {
            if (id == null || id.isBlank() || citizen == null || kind == null || evidence == null
                    || !Double.isFinite(distance + deficit + age + hunger) || distance < 0 || distance > 4096
                    || deficit < 0 || deficit > 1 || age < 0 || age > 1 || hunger < 0 || hunger > 1)
                throw new IllegalArgumentException("Invalid private village offer");
        }
        public double[] features() { return new double[] {1, Math.min(1, distance / 64), deficit, hunger}; }
    }
    public record Outcome(UUID job, UUID citizen, Kind kind, List<Double> features,
                          long start, long finish, double cost, boolean completed, String physicalReceipt) {
        public Outcome {
            features = List.copyOf(features);
            if (job == null || citizen == null || kind == null || features.size() != 4 || features.get(0) != 1
                    || features.stream().anyMatch(x -> !Double.isFinite(x) || x < 0 || x > 1)
                    || start < 0 || finish < start || finish-start > 24000 || !Double.isFinite(cost) || cost < 0 || cost > 1000
                    || physicalReceipt == null || (completed && kind != Kind.OBSERVE && kind != Kind.WAIT && physicalReceipt.isBlank()))
                throw new IllegalArgumentException("Invalid witnessed village outcome");
        }
    }
    public record Score(String id, double authoredValue, double predictedTicks, double predictedCost,
                        double success, double total, int privateSamples) {}
    private static final double[] PRIOR_TICKS = {100, 220, 100, 220, 60, 20, 20, 40};
    private static final double[] VALUES = {1.2, 1.8, 2.2, 3.2, 1.4, 5., .6, 0.};
    private static final class Fit {
        double[] weights = new double[4]; double[][] covariance = new double[4][4];
        Fit(double bias, double distance) { weights[0]=bias; weights[1]=distance; for(int i=0;i<4;i++)covariance[i][i]=1; }
        double predict(double[] x) { double v=0; for(int i=0;i<4;i++)v+=x[i]*weights[i];return v; }
        void learn(double[] x,double y) {
            double[] p=new double[4];for(int i=0;i<4;i++)for(int j=0;j<4;j++)p[i]+=covariance[i][j]*x[j];
            double denom=1;for(int i=0;i<4;i++)denom+=x[i]*p[i];double error=y-predict(x);
            for(int i=0;i<4;i++){weights[i]+=p[i]*error/denom;for(int j=0;j<4;j++)covariance[i][j]-=p[i]*p[j]/denom;}
        }
    }
    private final UUID owner;
    private final Fit[] duration=new Fit[8], cost=new Fit[8];
    private final int[] successes=new int[8], counts=new int[8];
    private final List<Outcome> outcomes=new ArrayList<>();
    private final HashSet<UUID> seen=new HashSet<>();
    public VillageWorkPolicy(UUID owner) {
        if(owner==null)throw new IllegalArgumentException("Missing private owner");this.owner=owner;
        for(int i=0;i<8;i++){duration[i]=new Fit(PRIOR_TICKS[i]/1200,384./1200);cost[i]=new Fit(0,.64);}
    }
    public Score score(Offer offer, boolean adaptive) {
        if(!offer.citizen().equals(owner))throw new IllegalArgumentException("Foreign private menu");
        int k=offer.kind().ordinal();double[] x=offer.features();
        double value=VALUES[k]*(.5+.5*offer.deficit());
        if(offer.kind()==Kind.EAT_BREAD)value*=.5+offer.hunger();
        if(offer.kind()==Kind.OBSERVE)value=.65+.3*offer.age();
        double ticks=adaptive?Math.max(0,duration[k].predict(x)*1200):PRIOR_TICKS[k]+6*offer.distance();
        double c=adaptive?Math.max(0,cost[k].predict(x)):.01*offer.distance();
        double success=adaptive?(successes[k]+3.)/(counts[k]+3.):1;
        // Observation optimism is explicitly authored, not a productivity reward.
        double total=offer.kind()==Kind.WAIT?0:success*value-.001*ticks-.25*c;
        if(offer.kind()==Kind.OBSERVE)total=Math.max(.03,total);
        return new Score(offer.id(),value,ticks,c,success,total,counts[k]);
    }
    public Offer choose(List<Offer> menu,boolean adaptive) {
        if(menu.isEmpty() || menu.size()>256)throw new IllegalArgumentException("Invalid menu size");
        var ids=new HashSet<String>();for(var offer:menu)if(!ids.add(offer.id()) || !offer.citizen().equals(owner))throw new IllegalArgumentException("Mixed/duplicate private menu");
        return menu.stream().min(Comparator.<Offer>comparingDouble(o->-score(o,adaptive).total()).thenComparing(Offer::id)).orElseThrow();
    }
    public boolean learn(Outcome outcome) {
        if(!outcome.citizen().equals(owner))throw new IllegalArgumentException("Foreign outcome");
        if(seen.contains(outcome.job())){
            if(outcomes.stream().noneMatch(outcome::equals))throw new IllegalArgumentException("Conflicting duplicate outcome");
            return false;
        }
        if(outcomes.size()>=MAX_OUTCOMES)throw new IllegalStateException("Private outcome capacity exhausted");
        if(!outcomes.isEmpty() && outcome.finish()<outcomes.get(outcomes.size()-1).finish())throw new IllegalArgumentException("Time-reversed outcome");
        double[] x=outcome.features().stream().mapToDouble(Double::doubleValue).toArray();int k=outcome.kind().ordinal();
        duration[k].learn(x,(outcome.finish()-outcome.start())/1200.);cost[k].learn(x,outcome.cost());
        counts[k]++;if(outcome.completed())successes[k]++;seen.add(outcome.job());outcomes.add(outcome);return true;
    }
    public List<Outcome> snapshot(){return List.copyOf(outcomes);}
    public static VillageWorkPolicy restore(UUID owner,List<Outcome> outcomes){var p=new VillageWorkPolicy(owner);for(var o:outcomes)p.learn(o);return p;}
}
