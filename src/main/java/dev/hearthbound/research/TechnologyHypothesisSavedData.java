package dev.hearthbound.research;

import java.util.ArrayList;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.saveddata.SavedData;

/** Per-dimension hypothesis persistence; no global unlock or fabricated evidence. */
public final class TechnologyHypothesisSavedData extends SavedData {
    private static final String KEY = "hearthbound_technology_hypotheses_v1";
    private final TechnologyHypotheses hypotheses = new TechnologyHypotheses();

    private TechnologyHypothesisSavedData() {}

    public static TechnologyHypothesisSavedData get(ServerLevel level) {
        return level.getDataStorage().computeIfAbsent(
            TechnologyHypothesisSavedData::load,
            TechnologyHypothesisSavedData::new, KEY);
    }

    public synchronized TechnologyHypotheses.Hypothesis propose(
            String agent, String recipe, String input, String machine, String output) {
        TechnologyHypotheses.Hypothesis h = hypotheses.propose(agent,recipe,input,machine,output);
        setDirty();
        return h;
    }

    public synchronized TechnologyHypotheses.Hypothesis observe(
            String agent, String recipe, String evidence, WorldEvidenceJournal journal) {
        TechnologyHypotheses.Hypothesis h = hypotheses.observe(agent,recipe,evidence,journal);
        setDirty();
        return h;
    }

    public synchronized TechnologyHypotheses.Hypothesis require(String agent, String recipe) {
        return hypotheses.require(agent,recipe);
    }

    public static TechnologyHypothesisSavedData load(CompoundTag root) {
        TechnologyHypothesisSavedData data = new TechnologyHypothesisSavedData();
        List<TechnologyHypotheses.Hypothesis> restored = new ArrayList<>();
        ListTag entries = root.getList("hypotheses",Tag.TAG_COMPOUND);
        for(int i=0;i<entries.size();i++) {
            CompoundTag h=entries.getCompound(i);
            String evidence=h.contains("evidence",Tag.TAG_STRING) ? h.getString("evidence") : null;
            restored.add(new TechnologyHypotheses.Hypothesis(
                h.getString("agent"), h.getString("recipe"), h.getString("input"),
                h.getString("machine"), h.getString("output"),
                TechnologyHypotheses.Status.valueOf(h.getString("status")), evidence));
        }
        data.hypotheses.restore(restored);
        return data;
    }

    @Override
    public synchronized CompoundTag save(CompoundTag root) {
        ListTag entries = new ListTag();
        for (TechnologyHypotheses.Hypothesis h : hypotheses.snapshot()) {
            CompoundTag row = new CompoundTag();
            row.putString("agent",h.agentId());
            row.putString("recipe",h.recipeId());
            row.putString("input",h.inputItem());
            row.putString("machine",h.machineType());
            row.putString("output",h.expectedOutput());
            row.putString("status",h.status().name());
            if (h.evidenceId()!=null) row.putString("evidence",h.evidenceId());
            entries.add(row);
        }
        root.put("hypotheses",entries);
        return root;
    }
}
