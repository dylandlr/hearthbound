package dev.hearthbound.ai;
public final class SurvivalPolicyTest {
    static void check(boolean ok) {if(!ok)throw new AssertionError();}
    static SurvivalPolicy.Observation o(double food,double hp,boolean edible,boolean threat,boolean night,boolean roof,int danger,int combat) {
        return new SurvivalPolicy.Observation(food,hp,edible,threat,night,roof,60,danger,combat,60);
    }
    public static void main(String[] args) {
        check(SurvivalPolicy.choose(o(2,1,true,true,false,false,70,30))==SurvivalPolicy.Action.FLEE);
        check(SurvivalPolicy.choose(o(20,1,false,true,false,false,25,75))==SurvivalPolicy.Action.DEFEND);
        check(SurvivalPolicy.choose(o(20,.3,false,true,false,false,25,75))==SurvivalPolicy.Action.FLEE);
        check(SurvivalPolicy.choose(o(2,1,true,false,false,false,50,50))==SurvivalPolicy.Action.EAT);
        check(SurvivalPolicy.choose(o(2,1,false,false,false,false,50,50))==SurvivalPolicy.Action.WORK);
        check(SurvivalPolicy.choose(o(20,1,false,false,true,true,50,50))==SurvivalPolicy.Action.SHELTER);
        check(SurvivalPolicy.choose(o(20,1,false,false,true,false,50,50))==SurvivalPolicy.Action.WORK);
        check(SurvivalPolicy.metabolize(.01,1)==0);
        check(SurvivalPolicy.metabolize(20,-1)==20);
        System.out.println("SurvivalPolicyTest PASS: emergency precedence, individuality, health adaptation, legal actions, hunger bounds");
    }
}
