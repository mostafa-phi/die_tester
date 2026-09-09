"""One-screen summary of a variant's result files (any machine).

    python remote/summary.py variants/r05
"""
import json
import sys
from pathlib import Path


def main() -> int:
    root = Path(sys.argv[1])
    s = json.loads((root / "static_r01.json").read_text())
    print(f"static: {s['status']}")
    for r in s["runs"]:
        c = r["cases"]
        print(f"  h {r['h_fine_mm']:.2f}  {r['dofs']:>9,} dofs  mesh {r['mesh_seconds']:6.1f}s solve {r['solve_seconds']:6.1f}s"
              f"  kY {c['Y']['k_guide_N_per_um']:.4f} kZ {c['Z']['k_guide_N_per_um']:.4f} N/um"
              f"  stroke {c['Y']['loaded_stroke']['minimum']['platform_um']:.1f}/{c['Y']['loaded_stroke']['nominal']['platform_um']:.1f} um"
              f"  vM {c['Y']['at_nominal_stroke']['peak_von_mises_MPa']:.0f}/{c['Z']['at_nominal_stroke']['peak_von_mises_MPa']:.0f} MPa")
    for name in ("modal_loaded_r01.json", "modal_r01.json"):
        p = root / name
        if not p.exists():
            continue
        m = json.loads(p.read_text())
        print(f"{name}: {m['status']}")
        for r in m["runs"]:
            f = r["sprung"]
            print(f"  h {r['h_fine_mm']:.2f}  {r['dofs']:>9,} dofs  setup {r['setup_seconds']:6.1f}s solve {r['solve_seconds']:6.1f}s  "
                  + ", ".join(f"{x:.0f} {mm['label']}" for x, mm in zip(f["frequencies_Hz"][:4], f["modes"][:4])))
    log = root / "work" / "chain.log"
    if log.exists():
        lines = [ln for ln in log.read_text().splitlines() if ln.startswith("===")]
        print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
