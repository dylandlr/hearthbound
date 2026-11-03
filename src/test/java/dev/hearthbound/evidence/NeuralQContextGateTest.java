package dev.hearthbound.evidence;

public final class NeuralQContextGateTest {
    private static int checks;
    static void check(boolean yes) {
        checks++;
        if(!yes) throw new AssertionError("context gate check="+checks);
    }
    static void invalid(double[] x) {
        try {
            NeuralQContextGate.classify(x,0);
            throw new AssertionError("Invalid v2 input accepted");
        } catch (IllegalArgumentException expected) {checks++;}
    }
    public static void main(String[] args) {
        for(int source=0;source<3;source++)
        for(int proposal=0;proposal<3;proposal++)
        for(int power=0;power<2;power++)
        for(int wheat=0;wheat<2;wheat++)
        for(int flour=0;flour<2;flour++)
        for(int blocked=0;blocked<2;blocked++)
        for(int busy=0;busy<2;busy++) {
            double[] x=new double[]{power,wheat,flour,blocked,0,
                source==0?1.:0.,source==1?1.:0.,source==2?1.:0.,busy,0};
            var d=NeuralQContextGate.classify(x,proposal);
            boolean valid=power==1&&wheat==0&&flour==0&&blocked==0&&busy==0
                &&source==proposal;
            check((d!=NeuralQContextGate.Decision.ABSTAIN)==valid);
            check(NeuralQContextGate.canProposeHaul(d)==(valid&&proposal==2));
        }
        double[] stale={1,0,0,0,0,1,0,0,0,1};
        check(NeuralQContextGate.classify(stale,0)==NeuralQContextGate.Decision.ABSTAIN);
        double[] bad={1,0,0,0,0,0,0,0,0,0}; invalid(bad);
        bad=new double[]{1,0,0,0,0,0,1,0,0,1}; invalid(bad);
        bad=new double[]{1,0,0,0,0,1,0,0,0,Double.NaN}; invalid(bad);
        check(NeuralQContextGate.classify(new double[]{0,0,0,0,0,1,0,0,0,0},0)
            ==NeuralQContextGate.Decision.ABSTAIN);
        check(NeuralQContextGate.classify(new double[]{1,0,1,0,0,1,0,0,0,0},2)
            ==NeuralQContextGate.Decision.ABSTAIN);
        System.out.println("PASS "+checks+" neural context gate safety and applicability tests");
    }
}
