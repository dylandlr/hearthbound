package dev.hearthbound.world;

import dev.hearthbound.research.AutonomousLibraryStudy;
import dev.hearthbound.research.LibraryStudyRuntime;
import java.util.UUID;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.entity.npc.Villager;

/**
 * Persisted per-citizen physical work ownership. This is independent of item
 * claims: a HAUL owner must still satisfy HaulClaims/MillReservations.
 * Never infer completion from elapsed time.
 */
public final class CitizenWorkOwnership {
    private static final String KEY = "hearthbound.workOwnerV1";
    public enum Kind { HAUL, STUDY }
    private CitizenWorkOwnership() {}

    public static void reconcile(Villager citizen) {
        CompoundTag tag = citizen.getPersistentData().getCompound(KEY);
        boolean hauling = SableHauling.active(citizen);
        boolean studying = AutonomousLibraryStudy.active(citizen)
                || LibraryStudyRuntime.state(citizen) == LibraryStudyRuntime.State.STUDYING;
        if (hauling && studying) {
            tag.putString("conflict", "Both physical executors active");
            citizen.getPersistentData().put(KEY, tag);
            return;
        }
        if (!hauling && !studying) {
            citizen.getPersistentData().remove(KEY);
            return;
        }
        Kind live = hauling ? Kind.HAUL : Kind.STUDY;
        if (tag.contains("kind") && !live.name().equals(tag.getString("kind"))) {
            tag.putString("conflict", "Persisted owner disagrees with physical executor");
            citizen.getPersistentData().put(KEY, tag);
            return;
        }
        // Recover a legacy assignment or a restarted server without generating
        // a new job identity for existing physical cargo.
        if (!tag.contains("kind")) {
            tag = new CompoundTag();
            tag.putString("kind", live.name());
            tag.putUUID("lease", UUID.randomUUID());
            citizen.getPersistentData().put(KEY, tag);
        }
    }

    public static void assertFree(Villager citizen) {
        reconcile(citizen);
        if (citizen.getPersistentData().contains(KEY))
            throw new IllegalStateException("Citizen already owns or has a conflicting physical work task");
    }

    public static void assigned(Villager citizen, Kind kind) {
        // Called only AFTER the physical executor accepted an assignment.
        reconcile(citizen);
        CompoundTag owner = citizen.getPersistentData().getCompound(KEY);
        if (!kind.name().equals(owner.getString("kind")))
            throw new IllegalStateException("Physical executor did not acquire expected work");
    }

    public static String status(Villager citizen) {
        CompoundTag owner = citizen.getPersistentData().getCompound(KEY);
        return owner.contains("conflict") ? "CONFLICT: " + owner.getString("conflict")
                : owner.contains("kind") ? owner.getString("kind") : "FREE";
    }
}
