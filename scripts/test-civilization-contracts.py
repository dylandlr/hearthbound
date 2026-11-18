#!/usr/bin/env python3
"""Compile/run real pure-Java policy suites; does not boot Forge."""
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parent.parent
    java = shutil.which("java")
    if not java:
        raise SystemExit("JDK 17+ with Java and compiler support is required")
    javac = shutil.which("javac")
    compiler = [javac] if javac else [java, "--module", "jdk.compiler/com.sun.tools.javac.Main"]
    sources = sorted((root / "src/main/java/dev/hearthbound/civilization").glob("*.java"))
    sources += sorted((root / "src/test/java/dev/hearthbound/civilization").glob("*.java"))
    tests = [p.stem for p in sources if p.name.endswith("Test.java")]
    if not tests:
        raise SystemExit("No civilization suites found")
    with tempfile.TemporaryDirectory(prefix="hearthbound-civilization-") as output:
        subprocess.run(compiler + ["--release", "17", "-encoding", "UTF-8", "-d", output]
                       + [str(p) for p in sources], cwd=root, check=True)
        for test in tests:
            subprocess.run([java, "-ea", "-cp", output,
                            "dev.hearthbound.civilization." + test], cwd=root, check=True)
    print(f"PASS {len(tests)} standalone Java civilization suites; Forge not executed")


if __name__ == "__main__":
    main()
