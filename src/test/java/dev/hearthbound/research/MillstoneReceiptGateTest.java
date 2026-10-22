package dev.hearthbound.research;
import java.util.List;
import java.util.UUID;
import dev.hearthbound.research.MillstoneReceiptGate.*;
public final class MillstoneReceiptGateTest {
  private static int checks;
  private static void ok(boolean value) { if (!value) throw new AssertionError(); checks++; }
  private static void rejects(Runnable r) { try {r.run(); throw new AssertionError("accepted invalid event");} catch(IllegalArgumentException expected) {checks++;} }
  public static void main(String[] ignored) {
    UUID id=UUID.randomUUID();
    Stack wheat=new Stack("minecraft:wheat",1), flour=new Stack("create:wheat_flour",1);
    InputProof p=new InputProof(id,"world","minecraft:overworld","1,64,2","create:milling/wheat",List.of(wheat));
    Completion c=new Completion("MILLSTONE",id,"world","minecraft:overworld","1,64,2","create:milling/wheat",List.of(flour));
    ok(MillstoneReceiptGate.validate(p,c).operationId().equals(id));
    ok(MillstoneReceiptGate.validate(p,c).consumed().equals(List.of(wheat)));
    rejects(()->MillstoneReceiptGate.validate(null,c));
    rejects(()->MillstoneReceiptGate.validate(p,new Completion("CRUSHING_WHEEL",id,"world","minecraft:overworld","1,64,2","create:milling/wheat",List.of(flour))));
    rejects(()->MillstoneReceiptGate.validate(p,new Completion("MILLSTONE",UUID.randomUUID(),"world","minecraft:overworld","1,64,2","create:milling/wheat",List.of(flour))));
    rejects(()->MillstoneReceiptGate.validate(p,new Completion("MILLSTONE",id,"other","minecraft:overworld","1,64,2","create:milling/wheat",List.of(flour))));
    rejects(()->MillstoneReceiptGate.validate(p,new Completion("MILLSTONE",id,"world","minecraft:the_nether","1,64,2","create:milling/wheat",List.of(flour))));
    rejects(()->MillstoneReceiptGate.validate(p,new Completion("MILLSTONE",id,"world","minecraft:overworld","2,64,2","create:milling/wheat",List.of(flour))));
    rejects(()->MillstoneReceiptGate.validate(p,new Completion("MILLSTONE",id,"world","minecraft:overworld","1,64,2","create:milling/other",List.of(flour))));
    rejects(()->MillstoneReceiptGate.validate(new InputProof(id,"world","minecraft:overworld","1,64,2","create:milling/wheat",List.of()),c));
    rejects(()->MillstoneReceiptGate.validate(p,new Completion("MILLSTONE",id,"world","minecraft:overworld","1,64,2","create:milling/wheat",List.of())));
    rejects(()->new Stack("wheat",1));
    rejects(()->new Stack("minecraft:wheat",0));
    System.out.println("MillstoneReceiptGate: "+checks+" checks passed");
  }
}
