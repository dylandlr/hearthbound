package dev.hearthbound.world;

import java.util.UUID;
import dev.hearthbound.evidence.WorldIdentityCodec;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.saveddata.SavedData;

/** A world-save-scoped identity stored only in Overworld SavedData. */
public final class HearthboundWorldIdentity extends SavedData {
    private static final String NAME = "hearthbound_world_identity_v1";
    private static final String KEY = "worldUuid";
    private final UUID id;

    private HearthboundWorldIdentity(UUID id) { this.id = id; }

    private static HearthboundWorldIdentity createNew() {
        HearthboundWorldIdentity data = new HearthboundWorldIdentity(WorldIdentityCodec.create());
        data.setDirty();
        return data;
    }

    private static HearthboundWorldIdentity load(CompoundTag tag) {
        if (!tag.contains(KEY, net.minecraft.nbt.Tag.TAG_STRING))
            throw new IllegalStateException("Existing Hearthbound world identity has no UUID");
        return new HearthboundWorldIdentity(WorldIdentityCodec.decode(tag.getString(KEY)));
    }

    @Override
    public CompoundTag save(CompoundTag tag) {
        tag.putString(KEY, WorldIdentityCodec.encode(id));
        return tag;
    }

    /** Access from the authoritative Minecraft server thread only. */
    public static UUID get(ServerLevel level) {
        ServerLevel overworld = level.getServer().getLevel(Level.OVERWORLD);
        if (overworld == null) throw new IllegalStateException("Overworld unavailable");
        return overworld.getDataStorage().computeIfAbsent(
            HearthboundWorldIdentity::load, HearthboundWorldIdentity::createNew, NAME).id;
    }

    /**
     * Inspect existing SavedData without creating an identity or marking it dirty.
     * Minecraft may cache data read from disk; no persistent or gameplay state is
     * created. A null result means no existing identity is available.
     */
    public static UUID peek(ServerLevel level) {
        ServerLevel overworld = level.getServer().getLevel(Level.OVERWORLD);
        if (overworld == null) return null;
        HearthboundWorldIdentity existing = overworld.getDataStorage().get(
            HearthboundWorldIdentity::load, NAME);
        return existing == null ? null : existing.id;
    }
}
