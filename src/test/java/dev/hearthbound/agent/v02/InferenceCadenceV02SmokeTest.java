package dev.hearthbound.agent.v02;

public final class InferenceCadenceV02SmokeTest {
    private static void verify(boolean condition, String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(String[] args) {
        verify(InferenceCadenceV02.shouldRun(100, -1, 20, false, false),
                "first inference suppressed");
        verify(!InferenceCadenceV02.shouldRun(119, 100, 20, false, false),
                "cadence ran early");
        verify(InferenceCadenceV02.shouldRun(120, 100, 20, false, false),
                "cadence missed boundary");
        verify(!InferenceCadenceV02.shouldRun(140, 100, 20, true, false),
                "inference overlapped active operation");
        verify(!InferenceCadenceV02.shouldRun(140, 100, 20, false, true),
                "inference ran after terminal state");
        System.out.println("PASS: v0.2 bounded inference cadence");
    }
}
