"""One table across variants: size, mass, aspect ratio, stiffness, stroke, stress, modes.

    python sweep_report.py r05 m6t50k21 m8t50k21 ...          (any machine, results must exist)
    python sweep_report.py --md ...                            markdown table for the README
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def row(name: str) -> dict:
    root = HERE / "variants" / name
    g = json.loads((root / "geometry_report.json").read_text(encoding="utf-8"))
    p, d = g["parameters"], g["derived"]
    box = d["box"]
    out = {
        "variant": name,
        "leaves": ("shim " if p.get("shim", False) else "milled ") + f"{p['t']:.2f} x {p['L']:.1f}",
        "b": p["b"], "aspect": (p["b"] / p["t"]) if not p.get("shim", False) else None,
        "plate_mm": f"{box[1] - box[0]:.0f} x {box[3] - box[2]:.0f} x {p['b']:.0f}",
        "mass_g": g["plate_mass_g"],
    }
    s = root / "static_r01.json"
    if s.exists():
        r = json.loads(s.read_text(encoding="utf-8"))["runs"][-1]
        c = r["cases"]
        out.update(k=(c["Y"]["k_guide_N_per_um"] + c["Z"]["k_guide_N_per_um"]) / 2,
                   stroke_min=c["Y"]["loaded_stroke"]["minimum"]["platform_um"],
                   stroke_nom=c["Y"]["loaded_stroke"]["nominal"]["platform_um"],
                   coupling=max(c["Y"]["at_nominal_stroke"]["coupling_pct"] + c["Z"]["at_nominal_stroke"]["coupling_pct"]),
                   vm=max(c["Y"]["at_nominal_stroke"]["peak_von_mises_MPa"], c["Z"]["at_nominal_stroke"]["peak_von_mises_MPa"]),
                   sag=r["gravity_loaded"]["platform_t_um"][2], h=r["h_fine_mm"])
    m = root / "modal_loaded_r01.json"
    if m.exists():
        r = json.loads(m.read_text(encoding="utf-8"))["runs"][-1]["sprung"]
        out["modes"] = ", ".join(f"{f:.0f} {x['label'].split(' ')[0]}" for f, x in zip(r["frequencies_Hz"][:3], r["modes"][:3]))
        out["f1"] = r["frequencies_Hz"][0]
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("variants", nargs="+")
    parser.add_argument("--md", action="store_true")
    args = parser.parse_args()
    rows = [row(v) for v in args.variants]
    head = ["variant", "leaves (t x L)", "plate (mm)", "b/t", "mass g", "k N/um", "stroke min/nom um",
            "coupling %", "vM MPa", "first modes (Hz)"]
    lines = []
    for r in rows:
        lines.append([r["variant"], r["leaves"], r["plate_mm"],
                      f"{r['aspect']:.0f}:1" if r["aspect"] else "-", f"{r['mass_g']:.0f}",
                      f"{r['k']:.4f}" if "k" in r else "-",
                      f"{r['stroke_min']:.0f} / {r['stroke_nom']:.0f}" if "k" in r else "-",
                      f"{r['coupling']:.2f}" if "k" in r else "-",
                      f"{r['vm']:.0f}" if "k" in r else "-",
                      r.get("modes", "-")])
    if args.md:
        print("| " + " | ".join(head) + " |")
        print("|" + "---|" * len(head))
        for ln in lines:
            print("| " + " | ".join(ln) + " |")
    else:
        widths = [max(len(h), *(len(ln[i]) for ln in lines)) for i, h in enumerate(head)]
        print("  ".join(h.ljust(w) for h, w in zip(head, widths)))
        for ln in lines:
            print("  ".join(c.ljust(w) for c, w in zip(ln, widths)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
