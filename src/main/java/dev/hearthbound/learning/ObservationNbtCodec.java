package dev.hearthbound.learning;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.DoubleTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;

/** Forge/Minecraft 1.20.1 compatible storage for fixed-width numeric observations. */
public final class ObservationNbtCodec {
    private ObservationNbtCodec() {}

    public static void put(CompoundTag parent, String key, double[] values) {
        if (parent == null || key == null || key.isBlank() || values == null)
            throw new IllegalArgumentException("invalid observation array");
        ListTag list = new ListTag();
        for (double value : values) {
            if (!Double.isFinite(value) || value < 0 || value > 1)
                throw new IllegalArgumentException("invalid normalized feature");
            list.add(DoubleTag.valueOf(value));
        }
        parent.put(key, list);
    }

    public static double[] get(CompoundTag parent, String key) {
        if (parent == null || key == null || key.isBlank()
                || !parent.contains(key, Tag.TAG_LIST))
            throw new IllegalArgumentException("missing observation array");
        ListTag values = parent.getList(key, Tag.TAG_DOUBLE);
        if (parent.get(key) instanceof ListTag original
                && !original.isEmpty() && original.getElementType() != Tag.TAG_DOUBLE)
            throw new IllegalArgumentException("invalid observation array element type");
        double[] result = new double[values.size()];
        for (int i = 0; i < result.length; i++) {
            result[i] = values.getDouble(i);
            if (!Double.isFinite(result[i]) || result[i] < 0 || result[i] > 1)
                throw new IllegalArgumentException("invalid observation feature");
        }
        return result;
    }
}
