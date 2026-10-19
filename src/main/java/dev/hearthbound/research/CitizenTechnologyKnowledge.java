package dev.hearthbound.research;

import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.world.entity.npc.Villager;

/**
 * Persistent per-citizen technology knowledge stored on the citizen entity.
 *
 * Knowledge is experiential: a recipe record must carry either direct physical evidence
 * or a teacher. Global scripted unlocks do not write here.
 */
public final class CitizenTechnologyKnowledge {
    private static final String KEY = "hearthbound.technologyKnowledgeV1";

    public enum Source {
        DIRECT_EXPERIMENT,
        TAUGHT,
        READ_BOOK
    }

    public record Entry(
            String recipeId,
            double confidence,
            Source source,
            String evidenceId,
            UUID teacher,
            long learnedTick) {}

    private CitizenTechnologyKnowledge() {}

    public static Entry discover(
            Villager citizen,
            String recipeId,
            String evidenceId,
            double confidence,
            long learnedTick) {

        validateRecipe(recipeId);
        if (evidenceId == null || evidenceId.isBlank())
            throw new IllegalArgumentException("Direct discovery requires evidenceId");
        Entry candidate = new Entry(
                recipeId,
                clamp(confidence),
                Source.DIRECT_EXPERIMENT,
                evidenceId,
                null,
                learnedTick);
        return upsert(citizen, candidate);
    }

    /**
     * Records a verified reading session. Reading supplies theoretical knowledge;
     * the confidence ceiling prevents books from replacing physical experimentation.
     * The caller must check book possession, readable page and completed study time.
     */
    public static Entry study(
            Villager citizen,
            String recipeId,
            String bookId,
            double readingProficiency,
            long learnedTick) {
        validateRecipe(recipeId);
        if (bookId == null || bookId.isBlank())
            throw new IllegalArgumentException("bookId must not be blank");
        if (!Double.isFinite(readingProficiency) || readingProficiency < 0 || readingProficiency > 1)
            throw new IllegalArgumentException("readingProficiency must be in [0,1]");
        double confidence = 0.10 + 0.30 * readingProficiency;
        return upsert(citizen, new Entry(recipeId, confidence, Source.READ_BOOK,
                "book:" + bookId, null, learnedTick));
    }

    public static Entry teach(
            Villager teacher,
            Villager student,
            String recipeId,
            long learnedTick) {

        Entry known = require(teacher, recipeId);
        double transmitted = clamp(Math.min(0.95, known.confidence() * 0.80));
        Entry candidate = new Entry(
                recipeId,
                transmitted,
                Source.TAUGHT,
                known.evidenceId(),
                teacher.getUUID(),
                learnedTick);
        return upsert(student, candidate);
    }

    public static boolean knows(Villager citizen, String recipeId) {
        return find(citizen, recipeId) != null;
    }

    public static Entry require(Villager citizen, String recipeId) {
        Entry entry = find(citizen, recipeId);
        if (entry == null)
            throw new IllegalStateException("Citizen does not know recipe " + recipeId);
        return entry;
    }

    /** Immutable snapshot of knowledge personally held by this citizen. */
    public static java.util.List<Entry> entries(Villager citizen) {
        ListTag stored = list(citizen);
        java.util.List<Entry> result = new java.util.ArrayList<>();
        for (int i = 0; i < stored.size(); i++) result.add(decode(stored.getCompound(i)));
        return java.util.List.copyOf(result);
    }

    public static String inspect(Villager citizen) {
        ListTag list = list(citizen);
        if (list.isEmpty()) return "TECH_KNOWLEDGE NONE";
        StringBuilder result = new StringBuilder("TECH_KNOWLEDGE ");
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) result.append(" | ");
            Entry e = decode(list.getCompound(i));
            result.append(e.recipeId())
                    .append(" confidence=").append(String.format(java.util.Locale.ROOT, "%.3f", e.confidence()))
                    .append(" source=").append(e.source())
                    .append(" evidence=").append(e.evidenceId());
            if (e.teacher() != null) result.append(" teacher=").append(e.teacher());
        }
        return result.toString();
    }

    private static Entry upsert(Villager citizen, Entry candidate) {
        ListTag list = list(citizen);
        for (int i = 0; i < list.size(); i++) {
            Entry current = decode(list.getCompound(i));
            if (!current.recipeId().equals(candidate.recipeId())) continue;
            if (candidate.confidence() > current.confidence()) {
                list.set(i, encode(candidate));
                save(citizen, list);
                return candidate;
            }
            return current;
        }
        list.add(encode(candidate));
        save(citizen, list);
        return candidate;
    }

    private static Entry find(Villager citizen, String recipeId) {
        validateRecipe(recipeId);
        ListTag list = list(citizen);
        for (int i = 0; i < list.size(); i++) {
            Entry entry = decode(list.getCompound(i));
            if (recipeId.equals(entry.recipeId())) return entry;
        }
        return null;
    }

    private static ListTag list(Villager citizen) {
        CompoundTag root = citizen.getPersistentData();
        CompoundTag knowledge = root.getCompound(KEY);
        if (!knowledge.contains("recipes", Tag.TAG_LIST)) return new ListTag();
        return knowledge.getList("recipes", Tag.TAG_COMPOUND).copy();
    }

    private static void save(Villager citizen, ListTag list) {
        CompoundTag knowledge = new CompoundTag();
        knowledge.put("recipes", list);
        citizen.getPersistentData().put(KEY, knowledge);
    }

    private static CompoundTag encode(Entry entry) {
        CompoundTag tag = new CompoundTag();
        tag.putString("recipe", entry.recipeId());
        tag.putDouble("confidence", entry.confidence());
        tag.putString("source", entry.source().name());
        tag.putString("evidence", entry.evidenceId());
        if (entry.teacher() != null) tag.putUUID("teacher", entry.teacher());
        tag.putLong("learnedTick", entry.learnedTick());
        return tag;
    }

    private static Entry decode(CompoundTag tag) {
        Source source = Source.valueOf(tag.getString("source"));
        UUID teacher = tag.hasUUID("teacher") ? tag.getUUID("teacher") : null;
        return new Entry(
                tag.getString("recipe"),
                tag.getDouble("confidence"),
                source,
                tag.getString("evidence"),
                teacher,
                tag.getLong("learnedTick"));
    }

    private static double clamp(double confidence) {
        if (!Double.isFinite(confidence))
            throw new IllegalArgumentException("confidence must be finite");
        return Math.max(0.05, Math.min(1.0, confidence));
    }

    private static void validateRecipe(String recipeId) {
        if (recipeId == null || recipeId.isBlank())
            throw new IllegalArgumentException("recipeId must not be blank");
    }
}
