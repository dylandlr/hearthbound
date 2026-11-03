package dev.hearthbound.evidence;

/** Pure Java shadow-policy checks: no game or policy-action execution. */
public final class MillPolicyShadowTest {
    private static int checks;
    private static void check(boolean value) {
        checks++;
        if (!value) throw new AssertionError("Check " + checks);
    }
    public static void main(String[] args) {
        var model=MillMlpInference.loadBundled();
        for (int p=0;p<2;p++)
            for (int w=0;w<2;w++)
                for (int f=0;f<2;f++)
                    for (int b=0;b<2;b++)
                        for (long experience:new long[]{0L,1L,5L,10L,100L}) {
                            var obs=new MillPolicyShadow.Observation(p==1,w==1,f==1,b==1,experience);
                            var scripted=MillPolicyShadow.decide(
                                MillPolicyShadow.Mode.SCRIPTED,obs,model);
                            var trained=MillPolicyShadow.decide(
                                MillPolicyShadow.Mode.TRAINED_MLP,obs,model);
                            check(scripted.selected()==scripted.reference());
                            check(MillPolicyShadow.allowed(obs,trained.selected()));
                            check(trained.rawMlp()!=null);
                        }
        var unpowered=new MillPolicyShadow.Observation(false,false,false,false,1L);
        check(!MillPolicyShadow.allowed(unpowered,MillPolicyShadow.Action.REQUEST_WHEAT_HAUL));
        check(MillPolicyShadow.allowed(unpowered,MillPolicyShadow.Action.INSPECT_UNPOWERED));
        var poweredWithWheat=new MillPolicyShadow.Observation(true,true,false,false,0L);
        check(!MillPolicyShadow.allowed(poweredWithWheat,MillPolicyShadow.Action.REQUEST_WHEAT_HAUL));
        check(!MillPolicyShadow.allowed(poweredWithWheat,MillPolicyShadow.Action.COLLECT_OUTPUT));
        try {
            new MillPolicyShadow.Observation(true,false,false,false,-1L);
            throw new AssertionError("negative experience was accepted");
        } catch (IllegalArgumentException expected) {checks++;}
        System.out.println("PASS "+checks+" shadow policy selection checks");
    }
}
