package dev.hearthbound.research;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import net.minecraft.world.entity.npc.Villager;

/**
 * Explicit technology offers, visible only when an opted-in teacher is nearby.
 * Offers contain recipe IDs only, never unseen research progress or private memories.
 */
public final class TechnologyOffers {
    private TechnologyOffers() {}

    public static List<String> advertisedBy(Villager teacher) {
        if (!CitizenSocialTeaching.enabled(teacher)) return List.of();
        List<String> recipes = new ArrayList<>();
        for (CitizenTechnologyKnowledge.Entry entry : CitizenTechnologyKnowledge.entries(teacher)) {
            if (entry.confidence() >= 0.15) recipes.add(entry.recipeId());
        }
        recipes.sort(Comparator.naturalOrder());
        return List.copyOf(recipes);
    }
}
