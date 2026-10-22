#!/usr/bin/env python3
"""Validate a Forge development JAR without starting Minecraft."""
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import sys

REQUIRED = {
    "META-INF/mods.toml",
    "dev/hearthbound/HearthboundMod.class",
    "dev/hearthbound/integration/MillstoneDiagnostics.class",
    "dev/hearthbound/integration/ForgeServerTickObserver.class",
    "dev/hearthbound/integration/HearthboundClockSavedData.class",
    "dev/hearthbound/research/MillstoneReceiptGate.class",
}

def main(argv):
    if len(argv) != 2:
        raise SystemExit("Usage: python3 scripts/verify_mod_jar.py <path-to-jar>")
    jar = Path(argv[1])
    if not jar.is_file():
        raise SystemExit(f"Missing mod JAR: {jar}")
    try:
        with ZipFile(jar) as archive:
            names = set(archive.namelist())
            missing = sorted(REQUIRED - names)
            if missing:
                raise SystemExit(f"Incomplete mod JAR; missing: {', '.join(missing)}")
            mods = archive.read("META-INF/mods.toml").decode("utf-8")
            for token in ('modId="hearthbound"', 'modId="create"'):
                if token not in mods:
                    raise SystemExit(f"Missing required mod metadata: {token}")
    except BadZipFile as exc:
        raise SystemExit(f"Invalid JAR archive: {exc}")
    print(f"Mod JAR structure validated: {jar} ({len(names)} entries)")

if __name__ == "__main__":
    main(sys.argv)
