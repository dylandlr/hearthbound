package dev.hearthbound.research;
import java.nio.file.Files;
import java.util.UUID;
public final class DurableCitizenInventoryTest {
    public static void main(String[] args) throws Exception {
        var dir = Files.createTempDirectory("citizen-inventory");
        var citizen = UUID.randomUUID();
        var operation = UUID.randomUUID();
        var first = new DurableCitizenInventory(dir, citizen, 1);
        if (first.available()!=1 || !first.reserve(operation) || first.available()!=0)
            throw new AssertionError("Reservation not persisted");
        var restart = new DurableCitizenInventory(dir, citizen, 1);
        if (restart.available()!=0 || restart.reserve(operation))
            throw new AssertionError("Reservation replayed on restart");
        boolean depleted=false;
        try { restart.reserve(UUID.randomUUID()); }
        catch (java.io.IOException expected) { depleted=true; }
        if (!depleted || restart.available()!=0) throw new AssertionError("Wheat overdraft");
        System.out.println("DurableCitizenInventory: 3 checks passed");
    }
}
