package dev.hearthbound.learning;

import dev.hearthbound.research.ResearchDecisionTraceJournal;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Durable job-to-policy provenance. A binding is NOT evidence or a reward. */
public final class PendingLearningBindingsSavedData extends SavedData {
    private static final String NAME = "hearthbound_pending_learning_bindings_v1";
    private static final int LIMIT = 10000;
    private final Map<UUID, VerifiedTrainingTransitions.Binding> pending = new LinkedHashMap<>();

    private PendingLearningBindingsSavedData() {}

    public static PendingLearningBindingsSavedData get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
                PendingLearningBindingsSavedData::load,
                PendingLearningBindingsSavedData::new, NAME);
    }

    public static PendingLearningBindingsSavedData load(CompoundTag root) {
        var data = new PendingLearningBindingsSavedData();
        ListTag entries = root.getList("bindings", Tag.TAG_COMPOUND);
        if (entries.size() > LIMIT) throw new IllegalStateException("oversized pending binding journal");
        for (int i = 0; i < entries.size(); i++) {
            CompoundTag e = entries.getCompound(i);
            UUID job = e.getUUID("job");
            UUID citizen = e.getUUID("citizen");
            var policy = new ResearchDecisionTraceJournal.PolicyDecision(
                    "PROPOSE", e.getString("recipe"), e.getDouble("utility"));
            var scripted = new ResearchDecisionTraceJournal.PolicyDecision(
                    e.getString("scriptedAction"), nullable(e.getString("scriptedRecipe")),
                    e.getDouble("scriptedUtility"));
            var trace = new ResearchDecisionTraceJournal.Trace(1, citizen.toString(), e.getLong("tick"),
                    scripted, policy, e.getBoolean("disagree"), e.getString("explanation"));
            var binding = new VerifiedTrainingTransitions.Binding(job, citizen, trace);
            validate(binding);
            if (data.pending.putIfAbsent(job, binding) != null)
                throw new IllegalStateException("duplicate pending job");
        }
        return data;
    }

    public synchronized void add(VerifiedTrainingTransitions.Binding binding) {
        validate(binding);
        var existing = pending.get(binding.job());
        if (existing != null && !existing.equals(binding))
            throw new IllegalStateException("conflicting pending job");
        if (existing == null) {
            if (pending.size() >= LIMIT) throw new IllegalStateException("pending binding capacity reached");
            pending.put(binding.job(), binding);
            setDirty();
        }
    }

    public synchronized VerifiedTrainingTransitions.Binding require(UUID job) {
        var binding = pending.get(job);
        if (binding == null) throw new IllegalStateException("no persisted decision binding for job " + job);
        return binding;
    }

    public synchronized void complete(UUID job) {
        if (pending.remove(job) != null) setDirty();
    }

    public synchronized int size() { return pending.size(); }

    @Override public synchronized CompoundTag save(CompoundTag root) {
        ListTag entries = new ListTag();
        for (var b : pending.values()) {
            var d = b.decision();
            CompoundTag e = new CompoundTag();
            e.putUUID("job", b.job()); e.putUUID("citizen", b.citizen());
            e.putLong("tick", d.gameTick());
            e.putString("recipe", d.personality().recipeId());
            e.putDouble("utility", d.personality().utility());
            e.putString("scriptedAction", d.scripted().action());
            e.putString("scriptedRecipe", d.scripted().recipeId() == null ? "" : d.scripted().recipeId());
            e.putDouble("scriptedUtility", d.scripted().utility());
            e.putBoolean("disagree", d.disagreement());
            e.putString("explanation", d.explanation());
            entries.add(e);
        }
        root.put("bindings", entries);
        return root;
    }

    private static String nullable(String value) { return value.isEmpty() ? null : value; }
    private static void validate(VerifiedTrainingTransitions.Binding b) {
        if (b == null || b.job() == null || b.citizen() == null
                || b.decision().gameTick() < 0
                || b.decision().personality().recipeId() == null
                || b.decision().personality().recipeId().isBlank())
            throw new IllegalArgumentException("invalid pending binding");
    }
}
