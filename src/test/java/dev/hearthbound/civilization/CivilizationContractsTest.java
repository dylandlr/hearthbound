package dev.hearthbound.civilization;
import java.util.*;
import dev.hearthbound.civilization.CivilizationContracts.*;
public final class CivilizationContractsTest {
  private static void verify(boolean yes) { if (!yes) throw new AssertionError("Failed assertion"); }
  public static void main(String[] args) {
    UUID self=UUID.randomUUID(),scout=UUID.randomUUID();
    Evidence direct=new Evidence(UUID.randomUUID(),self,self,"chest-A",EvidenceKind.DIRECT,10,10,3);
    Evidence reported=new Evidence(UUID.randomUUID(),scout,self,"chest-B",EvidenceKind.REPORTED,10,11,4);
    Set<ActionKind> actions=Set.of(ActionKind.GATHER,ActionKind.OBSERVE,ActionKind.WAIT);
    ScriptedPolicy policy=new ScriptedPolicy();
    Observation first=new Observation(self,12,List.of(direct,reported),actions);
    Decision gather=policy.decide(first); CivilizationContracts.validate(first,gather); verify(gather.action()==ActionKind.GATHER);
    Observation second=new Observation(self,12,List.of(reported),actions);
    Decision observe=policy.decide(second); CivilizationContracts.validate(second,observe); verify(observe.action()==ActionKind.OBSERVE);
    Observation third=new Observation(self,12,List.of(),actions); verify(policy.decide(third).action()==ActionKind.WAIT);
    verify(!new Outcome(gather.id(),true,false,13,0).worldEffectVerified());
    boolean rejected=false; try { CivilizationContracts.validate(second,gather); } catch (IllegalArgumentException e) { rejected=true; } verify(rejected);
    System.out.println("Civilization contracts: PASS");
  }
}
