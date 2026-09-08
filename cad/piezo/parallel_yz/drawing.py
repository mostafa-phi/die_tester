"""Dimensioned drawing of an R02 plate for the EDM shop: renders/drawing_r02.png.

    python -B drawing.py --variant r02

The profile is the back face of a coarse FE mesh of the plate (the same
geometry the DXF carries); the dimensions and notes come from
geometry_report.json, so the drawing cannot disagree with the model. The DXF
beside it (STEP/parallel_yz_r02_profile.dxf, mm, 1:1) is the cut file; this
sheet says what is not in the DXF: material, tolerances, the milled lands,
the tapped holes and the finishing.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import skfem  # noqa: E402

import fe_common as F  # noqa: E402
import mesh as meshing  # noqa: E402

PROFILE_H = 1.2


def dim_h(ax, y0, y1, z, text, offset=3.0, color="#1f4e79"):
    ax.annotate("", (y0, z), (y1, z), arrowprops=dict(arrowstyle="<->", color=color, lw=0.9))
    ax.text((y0 + y1) / 2, z + offset * 0.35, text, ha="center", va="bottom", fontsize=7.5, color=color)


def dim_v(ax, z0, z1, y, text, color="#1f4e79"):
    ax.annotate("", (y, z0), (y, z1), arrowprops=dict(arrowstyle="<->", color=color, lw=0.9))
    ax.text(y + 1.0, (z0 + z1) / 2, text, ha="left", va="center", fontsize=7.5, color=color, rotation=90)


def callout(ax, xy, xytext, text, color="#8b0000"):
    ax.annotate(text, xy=xy, xytext=xytext, fontsize=7.5, color=color, ha="left", va="center",
                arrowprops=dict(arrowstyle="->", color=color, lw=0.8, shrinkA=0, shrinkB=2))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    F.add_variant_argument(parser)
    args = parser.parse_args()
    F.set_variant(args.variant)
    rep = F.report()
    if "r02" not in rep:
        raise SystemExit("drawing.py needs an R02 variant (model.py --variant r02)")
    p, d, r = rep["parameters"], rep["derived"], rep["r02"]
    R = d["R"]

    msh = F.WORK / f"parallel_yz_r01_h{PROFILE_H:.2f}.msh"
    if not msh.exists():
        meshing.build(msh, PROFILE_H, loaded=False)
    m = skfem.MeshTet.load(msh)
    facets = m.facets_satisfying(lambda x: np.abs(x[0]) < 0.05, boundaries_only=True)
    tri = m.facets[:, facets]

    fig = plt.figure(figsize=(16.5, 11.7), dpi=150)          # A3 landscape
    ax = fig.add_axes([0.04, 0.06, 0.66, 0.88])
    ax.tripcolor(m.p[1], m.p[2], tri.T, facecolors=np.ones(tri.shape[1]), cmap="Greys",
                 vmin=0, vmax=2.2, edgecolors="none")
    ax.set_aspect("equal")
    # Room on the right for the callouts, so they never run into the notes block.
    ax.set_xlim(-R - 14, R + 70)
    ax.set_ylim(-R - 14, R + 14)
    ax.set_xlabel("Y (mm)")
    ax.set_ylabel("Z (mm)")
    variant = rep["variant"]
    shim = rep.get("shim", {}).get("enabled", False)
    millable = shim or (p["t"] >= 0.8 and p["b"] / p["t"] <= 10.5)
    process = ("CNC body + clamped shim leaves" if shim
               else "CNC-millable profile (or wire EDM)" if millable else "wire-EDM profile")
    ax.set_title(f"Parallel YZ flexure plate {variant} - {process}, viewed along the optical axis (+X toward viewer)\n"
                 f"{rep['actuator']['name']} in the +Y and +Z legs; scale from axes; DXF is the cut file",
                 fontsize=10)

    # Overall and pattern dimensions (the box is not centred on a two-leg plate).
    by0, by1, bz0, bz1 = d["box"]
    ax.set_xlim(by0 - 14, by1 + 70)
    ax.set_ylim(bz0 - 14, bz1 + 14)
    dim_h(ax, by0, by1, bz0 - 6, f"{by1 - by0:.1f}")
    dim_v(ax, bz0, bz1, by1 + 6, f"{bz1 - bz0:.1f}")
    pts = rep["fixture_mounted"]["points"]
    dim_h(ax, min(q[0] for q in pts), max(q[0] for q in pts), bz1 + 9,
          f"{max(q[0] for q in pts) - min(q[0] for q in pts):.1f}  (4 x dia {p['bolt']:.1f} thru)")
    dim_h(ax, -p["a_p"], p["a_p"], -p["a_p"] - 3.5, f"{2 * p['a_p']:.0f} platform")

    # Leg callouts (+Y leg).
    y_leaf = d["guide_y"][1]
    n_leaves = rep["edm"]["leaves"]
    if shim:
        callout(ax, (y_leaf, 18), (R + 18, 30),
                f"{n_leaves} shim leaves {p['t']:.2f} x {p['b']:.0f} x {p['L'] + 2 * p['tab']:.1f} "
                f"({p['leaf_material']['name'].split()[0]}),\nfree {p['L']:.1f} between bar edges; "
                f"thickness +/-0.005")
    else:
        callout(ax, (y_leaf, 18), (R + 18, 30),
                f"{n_leaves} leaves {p['t']:.2f} x {p['L']:.0f}, R{p['r_root']:.1f} roots\n"
                f"thickness {p['t']:.2f} +/-0.02, both faces parallel")
    callout(ax, ((d['pocket0'] + d['pocket1']) / 2, d['pocket_h']), (R + 18, 8),
            f"APA pocket {d['pocket1'] - d['pocket0']:.1f} x {2 * d['pocket_h']:.0f}\n"
            f"pad lands 2.5 x 5 x 0.2 raised, MILLED,\ncoplanar +/-0.02 (2 per driven leg)")
    callout(ax, (R, 0), (R + 18, -6),
            f"M2 clearance dia {r['screw_hole']:.1f} thru wall,\nc'bore dia {r['cbore']:.1f} x {r['cbore_frame']:.1f} from edge")
    callout(ax, (d["y_in0"], 0), (R + 18, -18),
            f"M2 clearance dia {r['screw_hole']:.1f} thru stage,\nc'bore dia {r['cbore']:.1f} x {r['cbore_stage']:.1f} from inner face")
    t0, t1 = r["tongue"]
    callout(ax, (p["a_p"] + 2, t1 + r["stop_gap"] / 2), (R + 18, -30),
            f"stops: tongue/fork, gap {r['stop_gap']:.2f} +0.10/-0\nx{len(p['legs'])} legs, profile feature")
    callout(ax, (0, 1.5), (R + 18, -42),
            f"dia {p['fiber_hole']:.0f} thru, {r['fiber_chamfer']:.1f} x 45 deg both faces\n"
            f"2 x M2 tapped {r['holder_tap_depth']:.0f} deep at Y +/-{r['holder_tap_y']:.1f} (front face)")
    if r["windows"]:
        w0, w1 = r["window"]
        callout(ax, (w0, w1), (R + 18, -54), f"4 corner windows {w1 - w0:.0f} sq")
    if r["wire_ties"]:
        wy, wz = r["wire_ties"][0]
        callout(ax, (wy, wz), (R + 18, 44), f"{len(r['wire_ties'])} x dia {r['wire_tie']:.0f} wire-tie holes")

    # Notes block.
    t, b = p["t"], p["b"]
    n_ties = len(r["wire_ties"])
    gap = d["pocket1"] - d["y_in1"] - 2 * p["pad_boss"]
    if shim:
        sh = rep["shim"]
        lm = p["leaf_material"]
        n_leaf = rep["edm"]["leaves"]
        process_notes = [
            f"BODY: CNC mill the profile from the DXF (mm, 1:1) in {rep['material']['name']}; it is 4 pieces",
            f"  (frame, 2 stages, platform) joined only by the leaves. Ledges/notches flat 0.01, no burrs.",
            f"LEAVES: {n_leaf} x {lm['name']}, {sh['leaf_t']:.2f} +/-0.005 thick, {sh['leaf_depth']:.0f} x "
            f"{sh['free_length'] + 2 * sh['tab']:.1f} rectangles, 2 x dia 2.4 holes per tab; shear/laser cut, deburr.",
            f"  Free length {sh['free_length']:.1f} between clamp-bar edges. Working stress ~200 MPa, 500 MPa at the stop.",
            f"CLAMPS: 16 bars {sh['leaf_depth']:.0f} x {sh['tab']:.1f} x {sh['bar_t']:.1f} (body material). "
            f"{len(sh['screws'])} x M2 x 6 into taps in the body",
            f"  (side-drilled along Y or Z) on the {len(sh['screws']) // 2} bars a driver can reach "
            f"({sum(1 for b_ in sh['bars'] if b_['access'] == 'angled')} of them ball-end only);",
            f"  the {sum(1 for b_ in sh['bars'] if b_['access'] == 'bond')} inner guide bars have no screw path: those tabs are EPOXY-BONDED (DP460 / EA 9460,",
            f"  jig-cured), bar as cure fixture. Bar inner edge R0.3 defines the root. Torque 0.3 N.m + thread-locker.",
            f"  Stop gaps {r['stop_gap']:.2f} +0.10/-0 are profile features of the body.",
        ]
    elif millable:
        process_notes = [
            f"PROCESS: CNC mill the through profile from the DXF (mm, 1:1) or wire EDM it, shop's choice.",
            f"  Leaves: {t:.2f} +/-0.02 thick, {b:.0f} deep ({b / t:.0f}:1 walls): finish with light passes,",
            f"  faces perpendicular to plate faces within 0.01 over {b:.0f}; no burrs on leaf edges.",
            f"  Stop gaps {r['stop_gap']:.2f} +0.10/-0: slot with a 0.3 mm cutter or one wire pass.",
        ]
    else:
        process_notes = [
            "PROCESS: wire EDM all through-cut features from the DXF (mm, 1:1), rough + 2 skim passes;",
            "  recast layer <= 5 um at leaf roots; no burrs on leaf edges. Start holes only in void areas.",
            f"  Leaves: {t:.2f} +/-0.02 thick, faces perpendicular to plate faces within 0.01 over {b:.0f}.",
            f"  Stop gaps {r['stop_gap']:.2f} are one wire pass: do not skim them narrower.",
        ]
    notes = [
        f"MATERIAL: {rep['material']['name']} plate, {b:.1f} mm, both faces ground flat 0.02 before profiling.",
        *process_notes,
        f"MILLING: 4 pad lands 2.5 x 5, raised {p['pad_boss']:.1f}, coplanar +/-0.02 per leg pair, land gap {gap:.2f} +0.05/-0",
        f"  (actuator is {p['apa_len']:.0f} +/-0.1: shim 0.05-0.15 at assembly); M2 clearance/counterbores on leg axes",
        f"  (4 places); 2 x M2 taps on the front face; 4 x dia {p['bolt']:.1f}; {n_ties} x dia {r['wire_tie']:.0f}.",
        "FINISH: bare, deburr, ultrasonic clean; no anodising on the leaves.",
        "ASSEMBLY: APA pads bolt to the lands with M2 SHCS (frame: from the edge; stage: from the coupler void,",
        "  ball-end key at <= 25 deg or stud + nut from the front). Torque per CEDRAT.",
        "  Fiber enters from the back through the base opening; APA wires exit the pocket at the back face.",
        f"MASS: plate {rep['plate_mass_g']:.0f} g; base {rep['base']['mass_g']:.0f} g.",
        f"CUTS: {rep['edm']['leaves']} leaves, {rep['edm']['closed_contours_to_thread']} closed contours, "
        f"{rep['edm']['cut_length_mm'] / 1000:.2f} m of profile.",
        f"SOURCE: cad/piezo/parallel_yz/model.py, variant {variant}; analysis in the README.",
    ]
    fig.text(0.715, 0.90, "NOTES", fontsize=10, weight="bold", va="top")
    fig.text(0.715, 0.87, "\n".join(notes), fontsize=7.0, va="top", family="monospace", linespacing=1.5)

    out = F.ROOT / "renders" / "drawing_r02.png"
    out.parent.mkdir(exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
