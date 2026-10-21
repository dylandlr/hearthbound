package dev.hearthbound.learning;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

class CitizenLocalStateSensorTest {
    @Test void snapshotRejectsMissingOrUnboundedFeatures() {
        assertThrows(IllegalArgumentException.class,
                () -> new CitizenLocalStateSensor.Snapshot(1,new double[3]));
        var invalid = new double[CitizenLocalStateSensor.WIDTH];
        invalid[4] = Double.NaN;
        assertThrows(IllegalArgumentException.class,
                () -> new CitizenLocalStateSensor.Snapshot(1,invalid));
    }

    @Test void snapshotDefensivelyCopiesFeatures() {
        var features = new double[CitizenLocalStateSensor.WIDTH];
        features[0] = .75;
        var snapshot = new CitizenLocalStateSensor.Snapshot(1,features);
        features[0] = 0;
        assertEquals(.75,snapshot.features()[0]);
        var copy = snapshot.features();
        copy[0] = 0;
        assertEquals(.75,snapshot.features()[0]);
    }
}
