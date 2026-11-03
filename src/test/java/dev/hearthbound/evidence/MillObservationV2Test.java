package dev.hearthbound.evidence;

import java.util.Arrays;

public final class MillObservationV2Test {
    private static int checks;
    private static void check(boolean ok) {
        checks++;
        if (!ok) throw new AssertionError("MillObservationV2 check " + checks);
    }
    private static void invalid(Runnable action) {
        try {
            action.run();
            throw new AssertionError("Invalid input accepted");
        } catch (IllegalArgumentException expected) { checks++; }
    }
    public static void main(String[] args) {
        check(MillObservationV2.FEATURES.size()==10);
        check(MillObservationV2.featureCsv().equals(
            "powered,mill_wheat_present,mill_flour_present,mill_blocked,"
            +"verified_experience_norm,source_unknown,source_empty,"
            +"source_available,task_active,source_stale"));
        for (boolean power:new boolean[]{false,true})
        for (boolean wheat:new boolean[]{false,true})
        for (boolean flour:new boolean[]{false,true})
        for (boolean blocked:new boolean[]{false,true})
        for (boolean busy:new boolean[]{false,true})
        for (MillObservationV2.SourceState state:MillObservationV2.SourceState.values())
        for (long age:new long[]{0,100,101,1000}) {
            var snapshot=new MillObservationV2.Snapshot(
                power,wheat,flour,blocked,20L,state,busy,1000L,1000L+age);
            var t=MillObservationV2.encode(snapshot);
            check(t.length==MillObservationV2.WIDTH);
            check(t[0]==(power?1:0) && t[1]==(wheat?1:0)
                && t[2]==(flour?1:0) && t[3]==(blocked?1:0));
            check(t[4]==1.0 && t[8]==(busy?1:0));
            boolean stale=state!=MillObservationV2.SourceState.UNKNOWN && age>100L;
            check(t[9]==(stale?1.0:0.0));
            check(t[5]+t[6]+t[7]==1.0);
            var expected=stale?MillObservationV2.SourceState.UNKNOWN:state;
            check(t[5]==(expected==MillObservationV2.SourceState.UNKNOWN?1.0:0.0));
            check(t[6]==(expected==MillObservationV2.SourceState.EMPTY?1.0:0.0));
            check(t[7]==(expected==MillObservationV2.SourceState.AVAILABLE?1.0:0.0));
        }
        var zero=new MillObservationV2.Snapshot(true,false,false,false,0,
            MillObservationV2.SourceState.AVAILABLE,false,0,0);
        check(MillObservationV2.encode(zero)[4]==0.0);
        var one=new MillObservationV2.Snapshot(true,false,false,false,1,
            MillObservationV2.SourceState.AVAILABLE,false,0,0);
        check(MillObservationV2.encode(one)[4]==0.1);
        invalid(() -> new MillObservationV2.Snapshot(true,false,false,false,-1,
            MillObservationV2.SourceState.UNKNOWN,false,0,0));
        invalid(() -> new MillObservationV2.Snapshot(true,false,false,false,0,
            null,false,0,0));
        invalid(() -> new MillObservationV2.Snapshot(true,false,false,false,0,
            MillObservationV2.SourceState.UNKNOWN,false,3,2));
        invalid(() -> new MillObservationV2.Snapshot(true,false,false,false,0,
            MillObservationV2.SourceState.UNKNOWN,false,-1,2));
        invalid(() -> MillObservationV2.encode(null));
        System.out.println("PASS "+checks+" mill observation v2 invariant checks");
    }
}
