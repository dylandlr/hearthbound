package dev.hearthbound.evidence;

import java.util.Objects;
import java.util.UUID;

/** Strict, pure Java world identity format; IDs are generated only at world creation. */
public final class WorldIdentityCodec {
    private WorldIdentityCodec() {}

    public static UUID create() { return UUID.randomUUID(); }

    public static String encode(UUID id) { return Objects.requireNonNull(id).toString(); }

    public static UUID decode(String stored) {
        if (stored == null || stored.length() != 36) throw new IllegalArgumentException("Invalid saved world UUID");
        final UUID id;
        try { id = UUID.fromString(stored); }
        catch (IllegalArgumentException ex) { throw new IllegalArgumentException("Invalid saved world UUID", ex); }
        if (!id.toString().equals(stored)) throw new IllegalArgumentException("Noncanonical saved world UUID");
        return id;
    }
}
