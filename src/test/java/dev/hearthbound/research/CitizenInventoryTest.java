package dev.hearthbound.research;
import java.util.UUID;
public final class CitizenInventoryTest {
    public static void main(String[] args) {
        UUID citizen = UUID.randomUUID();
        var inventory = new CitizenInventory.State(citizen, 2);
        var transfer = CitizenInventory.reserveWheat(inventory, citizen, 1);
        if (transfer.count() != 1 || transfer.next().wheat() != 1 || inventory.wheat() != 2)
            throw new AssertionError("Wheat not conserved in reservation");
        boolean rejected = false;
        try { CitizenInventory.reserveWheat(inventory, UUID.randomUUID(), 1); }
        catch (IllegalArgumentException expected) { rejected = true; }
        if (!rejected) throw new AssertionError("Foreign citizen inventory authorized");
        rejected = false;
        try { CitizenInventory.reserveWheat(new CitizenInventory.State(citizen, 0), citizen, 1); }
        catch (IllegalArgumentException expected) { rejected = true; }
        if (!rejected) throw new AssertionError("Missing inventory granted wheat");
        rejected = false;
        try { CitizenInventory.reserveWheat(inventory, citizen, 2); }
        catch (IllegalArgumentException expected) { rejected = true; }
        if (!rejected) throw new AssertionError("Bulk transfer accepted");
        System.out.println("CitizenInventory: 4 checks passed");
    }
}
