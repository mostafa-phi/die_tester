"""Zip this folder for the compute host (used by remote.ps1 up).

    python remote/pack.py <out.zip>

A zip carries no Unix modes, so OneDrive's read-only directory attribute cannot
leak into the extraction the way it does with tar. Meshes, VTU files, work/
logs and caches stay out; everything else (sources, variants, STEP, renders,
manufacturing) goes in.
"""
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"work", "__pycache__"}
SKIP_SUFFIXES = {".msh", ".vtu", ".zip"}


def main() -> int:
    out = Path(sys.argv[1])
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(HERE.rglob("*")):
            rel = path.relative_to(HERE)
            if not path.is_file() or any(part in SKIP_DIRS for part in rel.parts) or path.suffix in SKIP_SUFFIXES:
                continue
            data = path.read_bytes()
            if path.suffix in (".sh", ".py"):
                data = data.replace(b"\r\n", b"\n")
            z.writestr(zipfile.ZipInfo(f"parallel_yz/{rel.as_posix()}", date_time=(2026, 1, 1, 0, 0, 0)), data)
            n += 1
    print(f"{n} files -> {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
