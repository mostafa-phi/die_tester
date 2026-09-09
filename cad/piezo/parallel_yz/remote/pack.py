"""Zip this folder for the compute host (used by remote.ps1 up).

    python remote/pack.py <out.zip>

A zip carries no Unix modes, so OneDrive's read-only directory attribute cannot
leak into the extraction the way it does with tar. Sources, geometry reports
and STEP go in; meshes, logs, renders, manufacturing packages and the result
JSON files stay out (results only come back down, with `remote.ps1 fetch`).
"""
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"work", "__pycache__", "renders", "manufacturing"}
SKIP_SUFFIXES = {".msh", ".vtu", ".zip", ".png"}
# Results only travel host -> laptop (remote.ps1 fetch). Sending the local
# result files up would overwrite what a chain just computed there.
RESULT_FILES = {"static_r01.json", "modal_r01.json", "modal_loaded_r01.json"}


def main() -> int:
    out = Path(sys.argv[1])
    n = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(HERE.rglob("*")):
            rel = path.relative_to(HERE)
            if not path.is_file() or any(part in SKIP_DIRS for part in rel.parts) or path.suffix in SKIP_SUFFIXES:
                continue
            if path.name in RESULT_FILES:
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
