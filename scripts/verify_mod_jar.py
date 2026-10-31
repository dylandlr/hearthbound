#!/usr/bin/env python3
"""Validate a Forge development JAR without starting Minecraft."""
from pathlib import Path
from zipfile import ZipFile, BadZipFile
import sys

REQUIRED = {
    "META-INF/mods.toml",
    "hearthbound.mixins.json",
    "dev/hearthbound/mixin/MillstoneProcessMixin.class",
    "dev/hearthbound/mixin/MillstoneRecipeAccessor.class",
    "dev/hearthbound/integration/MillstoneMutationAudit.class",
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
            mixins = archive.read("hearthbound.mixins.json").decode("utf-8")
            if "MillstoneProcessMixin" not in mixins or "MillstoneRecipeAccessor" not in mixins:
                raise SystemExit("Millstone mixin missing from mixin configuration")
            manifest = archive.read("META-INF/MANIFEST.MF").decode("utf-8")
            if "MixinConfigs: hearthbound.mixins.json" not in manifest:
                raise SystemExit("Missing JAR MixinConfigs manifest attribute")
            for token in ('modId="hearthbound"', 'modId="create"'):
                if token not in mods:
                    raise SystemExit(f"Missing required mod metadata: {token}")
    except BadZipFile as exc:
        raise SystemExit(f"Invalid JAR archive: {exc}")
    print(f"Mod JAR structure validated: {jar} ({len(names)} entries)")

if __name__ == "__main__":
    main(sys.argv)
