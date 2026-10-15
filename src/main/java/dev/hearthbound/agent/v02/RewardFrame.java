package dev.hearthbound.agent.v02;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

public record RewardFrame(Map<String, Double> personalComponents,
                          Map<String, Double> colonyComponents) {
    public static final RewardFrame NONE = new RewardFrame(Map.of(), Map.of());

    public RewardFrame {
        personalComponents = immutableFinite(personalComponents, "personal");
        colonyComponents = immutableFinite(colonyComponents, "colony");
    }

    private static Map<String, Double> immutableFinite(Map<String, Double> input, String name) {
        if (input == null) throw new IllegalArgumentException(name);
        LinkedHashMap<String, Double> copy = new LinkedHashMap<>();
        input.forEach((key, value) -> {
            if (key == null || key.isBlank() || value == null || !Double.isFinite(value))
                throw new IllegalArgumentException("Invalid " + name + " reward component");
            copy.put(key, value);
        });
        return Collections.unmodifiableMap(copy);
    }

    public double personalTotal() {
        return personalComponents.values().stream().mapToDouble(Double::doubleValue).sum();
    }

    public double colonyTotal() {
        return colonyComponents.values().stream().mapToDouble(Double::doubleValue).sum();
    }
}
