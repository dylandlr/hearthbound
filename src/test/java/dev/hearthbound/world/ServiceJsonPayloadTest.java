package dev.hearthbound.world;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.util.List;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.Tag;

/** Actual Minecraft NBT round trips, including histories larger than writeUTF supports. */
public final class ServiceJsonPayloadTest {
    private static CompoundTag roundTrip(CompoundTag root) throws Exception {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        NbtIo.write(root, new DataOutputStream(bytes));
        return NbtIo.read(new DataInputStream(new ByteArrayInputStream(bytes.toByteArray())));
    }

    public static void main(String[] args) throws Exception {
        for (String payload : List.of("[]", "x".repeat(225_015), "\u0000\u00e9\u6c34\ud83e\udde0".repeat(40_000))) {
            CompoundTag root = new CompoundTag();
            for (String key : List.of("records", "kernel", "snapshot")) ServiceJsonPayload.write(root, key, payload);
            CompoundTag restored = roundTrip(root);
            for (String key : List.of("records", "kernel", "snapshot")) {
                if (!restored.contains(key, Tag.TAG_BYTE_ARRAY) || !payload.equals(ServiceJsonPayload.read(restored, key)))
                    throw new AssertionError("NBT history was truncated or changed: " + key);
            }
        }
        CompoundTag legacy = new CompoundTag(); legacy.putString("records", "[{\"sequence\":1}]");
        if (!ServiceJsonPayload.read(roundTrip(legacy), "records").equals("[{\"sequence\":1}]"))
            throw new AssertionError("Legacy schema-1 string was lost");
        for (int invalid = 0; invalid < 3; invalid++) {
            CompoundTag root = new CompoundTag();
            if (invalid == 1) root.putInt("records", 1);
            if (invalid == 2) root.putByteArray("records", new byte[] {(byte) 0xc3, 0x28});
            try {
                ServiceJsonPayload.read(roundTrip(root), "records");
                throw new AssertionError("Invalid saved payload accepted");
            } catch (IllegalStateException expected) { }
        }
        System.out.println("PASS service JSON real NBT persistence: large histories, Unicode, legacy saves, malformed data");
        VillageDataTest.main(args);
    }
}
