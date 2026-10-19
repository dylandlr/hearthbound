package dev.hearthbound.research;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Counterfactual policy comparison over exactly the same partial observation.
 * A computed comparison is diagnostic only; it never issues actions or changes
 * research evidence, claims, inventories, or learning state.
 */
public final class ResearchDecisionComparison {
    public record Comparison(int schemaVersion, ResearchPolicyBaselines.Decision scripted,
                             ResearchPolicyBaselines.Decision personality,
                             boolean disagree, Map<String, Double> utilityByMode,
                             String explanation) {}
    private ResearchDecisionComparison() {}
    public static Comparison evaluate(ExperimentSelectionPolicy.Observation observed) {
        var scripted=ResearchPolicyBaselines.choose(ResearchPolicyBaselines.Mode.SCRIPTED, observed);
        var personality=ResearchPolicyBaselines.choose(ResearchPolicyBaselines.Mode.PERSONALITY, observed);
        boolean disagree=scripted.choice().action()!=personality.choice().action()
                || (scripted.choice().candidate()!=null && personality.choice().candidate()!=null
                && !scripted.choice().candidate().recipeId().equals(
                    personality.choice().candidate().recipeId()));
        Map<String,Double> utility=new LinkedHashMap<>();
        utility.put("SCRIPTED",scripted.choice().utility());
        utility.put("PERSONALITY",personality.choice().utility());
        String reason=disagree
                ? "Different action eligibility thresholds or candidate rankings under fixed versus observed curiosity"
                : "Both policies selected the same action with the available observations";
        return new Comparison(1,scripted,personality,disagree,Map.copyOf(utility),reason);
    }
}
