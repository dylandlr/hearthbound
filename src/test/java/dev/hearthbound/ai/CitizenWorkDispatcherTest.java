package dev.hearthbound.ai;

import dev.hearthbound.research.CitizenTaskArbiter;
import java.util.List;
import java.util.UUID;
import static dev.hearthbound.ai.ColonyPolicy.*;

public final class CitizenWorkDispatcherTest {
    static void check(boolean value,String name) { if (!value) throw new AssertionError(name); }
    public static void main(String[] args) {
        UUID id=UUID.randomUUID();
        var arbiter=new CitizenTaskArbiter();
        var dispatch=new CitizenWorkDispatcher(arbiter);
        var action=new Action("study:library",Kind.STUDY,1,true);
        var obs=new Observation(42,id.toString(),0,0,0,List.of(action));
        ColonyPolicy choose=o -> new Decision(o.version(),"study:library","study is preferred");
        var assigned=dispatch.dispatch(id,obs,choose,(a,lease)->true);
        check(assigned.accepted(),"accepted study");
        check(assigned.lease().kind()==CitizenTaskArbiter.Kind.STUDY,"study lease");
        check(!dispatch.dispatch(id,obs,choose,(a,l)->true).accepted(),"cannot double assign");
        check(!dispatch.complete(id,UUID.randomUUID()),"stale release rejected");
        check(dispatch.complete(id,assigned.lease().assignmentId()),"release owner");
        var rejected=dispatch.dispatch(id,obs,choose,(a,l)->false);
        check(!rejected.accepted() && arbiter.active(id)==null,"declined executor rolls back lease");
        ColonyPolicy stale=o -> new Decision(41,"study:library","stale");
        check(!dispatch.dispatch(id,obs,stale,(a,l)->true).accepted(),"stale decision");
        ColonyPolicy unsupported=o -> new Decision(42,"study:library","test");
        var unsupportedObs=new Observation(42,id.toString(),0,0,0,
                List.of(new Action("follow",Kind.FOLLOW,1,true)));
        check(!dispatch.dispatch(id,unsupportedObs,
                o -> new Decision(42,"follow","not implemented"),(a,l)->true).accepted(),
                "unsupported kind rejected");
        check(dispatch.traces().size()==5,"trace count");
        var restored = new CitizenWorkDispatcher(new CitizenTaskArbiter());
        restored.restore(id, assigned.lease());
        restored.restore(id, assigned.lease());
        check(!restored.dispatch(id,obs,choose,(a,l)->true).accepted(),
                "restored assignment blocks duplicate work");
        check(restored.complete(id,assigned.lease().assignmentId()),
                "restored assignment can complete");
        check(restored.dispatch(id,obs,choose,(a,l)->true).accepted(),
                "new assignment accepted after reconciliation");
        System.out.println("CitizenWorkDispatcherTest: 11 checks passed");
    }
}
