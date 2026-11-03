package dev.hearthbound.evidence;

import java.util.Arrays;
import java.util.Objects;

/** Java 17 standalone test against the exact trained, bundled MLP resource. */
public final class MillMlpInferenceTest {
    public static void main(String[] args) {
        MillMlpInference inference=MillMlpInference.loadBundled();
        int checks=0;
        for (int power=0;power<2;power++) {
            for (int wheat=0;wheat<2;wheat++) {
                for (int flour=0;flour<2;flour++) {
                    for (int blocked=0;blocked<2;blocked++) {
                        MillMlpInference.Action expected=power==0
                            ? MillMlpInference.Action.INSPECT_UNPOWERED
                            : flour==1 || blocked==1 ? MillMlpInference.Action.COLLECT_OUTPUT
                            : wheat==1 ? MillMlpInference.Action.WAIT_FOR_PROCESSING
                            : MillMlpInference.Action.REQUEST_WHEAT_HAUL;
                        for (long experience : new long[]{0,1,5,10,100}) {
                            var actual=inference.predict(power==1,wheat==1,flour==1,blocked==1,experience);
                            if (actual!=expected) throw new AssertionError(
                                "Mismatch p="+power+" w="+wheat+" f="+flour+" b="+blocked+
                                " e="+experience+" expected="+expected+" actual="+actual);
                            checks++;
                        }
                    }
                }
            }
        }
        try {
            inference.predict(true,false,false,false,-1);
            throw new AssertionError("negative experience permitted");
        } catch(IllegalArgumentException expected) {checks++;}
        try {
            MillMlpInference.parse(new byte[]{1,2,3});
            throw new AssertionError("corrupted model accepted");
        } catch(IllegalArgumentException expected) {checks++;}
        System.out.println("PASS "+checks+" trained MLP parity and integrity checks");
    }
}
