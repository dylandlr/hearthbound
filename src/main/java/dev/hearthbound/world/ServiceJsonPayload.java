package dev.hearthbound.world;

import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.Tag;

/** JSON histories can exceed NBT's 65,535-byte modified-UTF string limit. */
final class ServiceJsonPayload {
    private ServiceJsonPayload() {}

    static void write(CompoundTag tag, String key, String json) {
        tag.putByteArray(key, json.getBytes(StandardCharsets.UTF_8));
    }

    static String read(CompoundTag tag, String key) {
        // Existing schema-1 saves used strings. New saves use byte arrays for
        // the kernel, records, and each private learner without losing history.
        if (tag.contains(key, Tag.TAG_STRING)) return tag.getString(key);
        if (!tag.contains(key, Tag.TAG_BYTE_ARRAY))
            throw new IllegalStateException("Missing or invalid service JSON payload: " + key);
        try {
            return StandardCharsets.UTF_8.newDecoder()
                .onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT)
                .decode(ByteBuffer.wrap(tag.getByteArray(key))).toString();
        } catch (CharacterCodingException invalid) {
            throw new IllegalStateException("Invalid UTF-8 in service JSON payload: " + key, invalid);
        }
    }
}
