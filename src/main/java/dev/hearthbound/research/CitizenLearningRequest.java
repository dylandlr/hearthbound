package dev.hearthbound.research;

import net.minecraft.world.entity.npc.Villager;
import net.minecraft.nbt.CompoundTag;

/**
 * Local, persistent request to learn a specific recipe.
 * Requests are deliberate citizen state, not shared omniscient knowledge.
 */
public final class CitizenLearningRequest {
    private static final String KEY = "hearthbound.learningRequestV1";
    private CitizenLearningRequest() {}

    public static void request(Villager student, String recipe) {
        if (recipe == null || recipe.isBlank()) throw new IllegalArgumentException("Missing recipe");
        if (CitizenTechnologyKnowledge.knows(student, recipe))
            throw new IllegalStateException("Student already knows recipe");
        CompoundTag data = new CompoundTag();
        data.putString("recipe", recipe);
        student.getPersistentData().put(KEY, data);
    }
    public static boolean requests(Villager student, String recipe) {
        return recipe != null && recipe.equals(student.getPersistentData()
                .getCompound(KEY).getString("recipe"));
    }
    public static void fulfilled(Villager student, String recipe) {
        if (requests(student, recipe)) student.getPersistentData().remove(KEY);
    }
    public static String inspect(Villager student) {
        String recipe = student.getPersistentData().getCompound(KEY).getString("recipe");
        return recipe.isBlank() ? "LEARNING_REQUEST NONE" : "LEARNING_REQUEST recipe=" + recipe;
    }
}
