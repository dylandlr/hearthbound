package dev.hearthbound.ai;

/** Version 1 scripted baseline. All inputs are local observations, not hidden world state. */
public final class SurvivalPolicy {
    public enum Action { WORK, EAT, FLEE, DEFEND, SHELTER }
    public record Observation(double food, double health, boolean foodAvailable,
            boolean threatVisible, boolean night, boolean shelterAvailable,
            int foodInstinct, int dangerInstinct, int combatInstinct, int shelterInstinct) {}
    private SurvivalPolicy() {}
    public static Action choose(Observation o) {
        if (o.threatVisible()) {
            if (o.health() < .6 || o.dangerInstinct() >= o.combatInstinct()) return Action.FLEE;
            return Action.DEFEND;
        }
        if (o.foodAvailable() && o.food() <= 6 + o.foodInstinct() * .1) return Action.EAT;
        if (o.night() && o.shelterAvailable() && o.shelterInstinct() >= 40) return Action.SHELTER;
        return Action.WORK;
    }
    public static double metabolize(double food, double seconds) {
        return Math.max(0, Math.min(20, food) - Math.max(0, seconds) * .02);
    }
}
