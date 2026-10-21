package dev.hearthbound.learning;

import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.StringTag;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class ObservationNbtCodecTest {
    @Test void exactDoubleValuesSurviveMinecraftTagRoundTrip() {
        var root = new CompoundTag();
        double[] values = {0, .375, 1};
        ObservationNbtCodec.put(root, "features", values);
        assertArrayEquals(values, ObservationNbtCodec.get(root, "features"));
        values[0] = 1;
        assertEquals(0, ObservationNbtCodec.get(root, "features")[0]);
    }
    @Test void rejectsMissingWrongTypeOrOutOfRange() {
        var root = new CompoundTag();
        assertThrows(IllegalArgumentException.class, () -> ObservationNbtCodec.get(root, "features"));
        var invalid = new ListTag();
        invalid.add(StringTag.valueOf("bad"));
        root.put("features", invalid);
        assertThrows(IllegalArgumentException.class, () -> ObservationNbtCodec.get(root, "features"));
        assertThrows(IllegalArgumentException.class,
            () -> ObservationNbtCodec.put(new CompoundTag(),"features",new double[]{Double.NaN}));
    }
}
